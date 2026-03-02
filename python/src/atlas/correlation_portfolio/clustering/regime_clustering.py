"""
Regime Clustering — Asset Clustering by Return Similarity
===========================================================
Groups assets into clusters based on correlation/return patterns.

Methods:
  1. Hierarchical Clustering (Ward linkage on correlation distance)
  2. K-Means on rolling return vectors (regime-aware)
  3. PCA-based cluster visualization data

Use cases:
  - Portfolio diversification (pick one from each cluster)
  - Regime change detection (cluster composition shifts)
  - Risk concentration monitoring

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.clustering")


@dataclass
class ClusterResult:
    n_clusters: int
    labels: Dict[str, int]           # ticker → cluster id
    cluster_members: Dict[int, List[str]]  # cluster_id → [tickers]
    cluster_centroids: Dict[int, np.ndarray]  # cluster_id → centroid return vector
    intra_cluster_corr: Dict[int, float]  # avg corr within each cluster
    inter_cluster_corr: float         # avg corr across clusters
    silhouette_score: float           # -1 to 1, higher = better separation
    pca_coords: Dict[str, Tuple[float, float]]  # 2D coords for visualization


class RegimeClusterer:
    """
    Clusters assets by return similarity using hierarchical and PCA methods.

    Usage
    -----
    clusterer = RegimeClusterer(n_clusters=4)
    result    = clusterer.cluster(prices_df)
    """

    def __init__(
        self,
        n_clusters: int = 4,
        lookback: int = 126,
        method: str = "hierarchical",   # "hierarchical" | "kmeans"
    ):
        self.n_clusters = n_clusters
        self.lookback   = lookback
        self.method     = method

    # ── Distance / Similarity ────────────────────────────────────

    @staticmethod
    def _corr_distance(corr_matrix: pd.DataFrame) -> np.ndarray:
        """Convert correlation matrix to distance matrix: d = sqrt(2(1-ρ))."""
        return np.sqrt(2 * (1 - corr_matrix.values))

    # ── Hierarchical (Ward) ───────────────────────────────────────

    def _hierarchical_cluster(
        self, dist_matrix: np.ndarray, tickers: List[str]
    ) -> Dict[str, int]:
        """
        Ward's minimum variance hierarchical clustering.
        Pure numpy implementation — no scipy required.
        """
        n = len(tickers)
        if n <= self.n_clusters:
            return {t: i for i, t in enumerate(tickers)}

        # Initialize: each asset is its own cluster
        clusters = {i: [i] for i in range(n)}
        distances = dist_matrix.copy().astype(float)
        np.fill_diagonal(distances, np.inf)

        while len(clusters) > self.n_clusters:
            # Find pair with minimum Ward distance
            min_d = np.inf
            merge_a, merge_b = 0, 1
            cluster_keys = list(clusters.keys())
            for i_idx, i in enumerate(cluster_keys):
                for j in cluster_keys[i_idx + 1:]:
                    # Ward distance proxy: mean of pairwise distances
                    members_i = clusters[i]
                    members_j = clusters[j]
                    d_vals = [dist_matrix[a, b] for a in members_i for b in members_j]
                    d = float(np.mean(d_vals)) if d_vals else np.inf
                    if d < min_d:
                        min_d = d
                        merge_a, merge_b = i, j

            # Merge clusters
            clusters[merge_a] = clusters[merge_a] + clusters[merge_b]
            del clusters[merge_b]

        # Assign cluster labels
        labels = {}
        for label, (cluster_id, members) in enumerate(clusters.items()):
            for idx in members:
                labels[tickers[idx]] = label

        return labels

    # ── K-Means ───────────────────────────────────────────────────

    def _kmeans_cluster(
        self, return_matrix: np.ndarray, tickers: List[str]
    ) -> Dict[str, int]:
        """Simple K-Means clustering on return vectors."""
        n, d = return_matrix.shape
        k = min(self.n_clusters, n)

        # Initialize centroids (K-Means++)
        centroids = [return_matrix[np.random.randint(n)]]
        for _ in range(k - 1):
            dists = np.array([
                min(float(np.linalg.norm(x - c)) for c in centroids)
                for x in return_matrix
            ])
            probs = dists / (dists.sum() + 1e-10)
            idx = np.random.choice(n, p=probs)
            centroids.append(return_matrix[idx])

        centroids = np.array(centroids)

        for _ in range(50):
            # Assign
            labels_arr = np.argmin(
                np.linalg.norm(return_matrix[:, None] - centroids[None, :], axis=2), axis=1
            )
            # Update
            new_centroids = np.array([
                return_matrix[labels_arr == k_].mean(axis=0)
                if (labels_arr == k_).any() else centroids[k_]
                for k_ in range(k)
            ])
            if np.allclose(new_centroids, centroids, atol=1e-6):
                break
            centroids = new_centroids

        return {tickers[i]: int(labels_arr[i]) for i in range(n)}

    # ── PCA Coordinates ──────────────────────────────────────────

    @staticmethod
    def _pca_2d(return_matrix: np.ndarray, tickers: List[str]) -> Dict[str, Tuple[float, float]]:
        """Project assets to 2D using top-2 PCA components."""
        X = return_matrix - return_matrix.mean(axis=0)
        if X.shape[0] < 2 or X.shape[1] < 2:
            return {t: (float(i), 0.0) for i, t in enumerate(tickers)}
        try:
            U, S, Vt = np.linalg.svd(X, full_matrices=False)
            coords = U[:, :2] * S[:2]
            return {tickers[i]: (round(float(coords[i, 0]), 4), round(float(coords[i, 1]), 4))
                    for i in range(len(tickers))}
        except Exception:
            return {t: (float(i), 0.0) for i, t in enumerate(tickers)}

    # ── Quality Metrics ────────────────────────────────────────

    @staticmethod
    def _silhouette(dist_matrix: np.ndarray, labels: Dict[str, int], tickers: List[str]) -> float:
        """Simplified silhouette score."""
        n = len(tickers)
        if n < 3:
            return 0.0
        label_arr = np.array([labels[t] for t in tickers])
        scores = []
        for i in range(n):
            same_mask  = (label_arr == label_arr[i]) & (np.arange(n) != i)
            other_mask = label_arr != label_arr[i]
            if not same_mask.any() or not other_mask.any():
                continue
            a = float(dist_matrix[i, same_mask].mean())
            b_clusters = np.unique(label_arr[other_mask])
            b = min(float(dist_matrix[i, label_arr == c].mean()) for c in b_clusters)
            scores.append((b - a) / (max(a, b) + 1e-10))
        return round(float(np.mean(scores)), 4) if scores else 0.0

    # ── Main ──────────────────────────────────────────────────────

    def cluster(self, prices: pd.DataFrame) -> ClusterResult:
        """
        Cluster assets by return similarity.

        Parameters
        ----------
        prices : DataFrame with Date index, ticker columns (close prices)
        """
        returns = prices.pct_change().dropna().iloc[-self.lookback:]
        tickers = list(returns.columns)
        n = len(tickers)

        if n < 2:
            raise ValueError("Need at least 2 assets to cluster")

        # Return matrix for K-Means / PCA
        return_matrix = returns.T.values   # shape (n_tickers, n_days)

        # Correlation and distance matrix
        corr_matrix = returns.corr()
        dist_matrix = self._corr_distance(corr_matrix)

        # Clustering
        if self.method == "hierarchical":
            labels = self._hierarchical_cluster(dist_matrix, tickers)
        else:
            labels = self._kmeans_cluster(return_matrix, tickers)

        cluster_ids = sorted(set(labels.values()))
        cluster_members = {c: [t for t, l in labels.items() if l == c] for c in cluster_ids}

        # Centroids in return space
        centroids = {}
        for c, members in cluster_members.items():
            member_idx = [tickers.index(t) for t in members]
            centroids[c] = return_matrix[member_idx].mean(axis=0)

        # Quality metrics
        sil = self._silhouette(dist_matrix, labels, tickers)
        pca_coords = self._pca_2d(return_matrix, tickers)

        # Intra-cluster correlation
        intra = {}
        for c, members in cluster_members.items():
            if len(members) < 2:
                intra[c] = 1.0
            else:
                vals = [corr_matrix.loc[a, b] for i, a in enumerate(members)
                        for b in members[i + 1:]]
                intra[c] = round(float(np.mean(vals)), 4)

        # Inter-cluster correlation
        inter_vals = [corr_matrix.loc[a, b]
                      for c1, m1 in cluster_members.items()
                      for c2, m2 in cluster_members.items()
                      if c1 < c2
                      for a in m1 for b in m2]
        inter = round(float(np.mean(inter_vals)), 4) if inter_vals else 0.0

        return ClusterResult(
            n_clusters=len(cluster_ids),
            labels=labels,
            cluster_members=cluster_members,
            cluster_centroids=centroids,
            intra_cluster_corr=intra,
            inter_cluster_corr=inter,
            silhouette_score=sil,
            pca_coords=pca_coords,
        )
