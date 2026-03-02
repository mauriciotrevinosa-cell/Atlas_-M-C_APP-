"""
ATLAS 3D Visualization Engine
================================
Generates 3D surface plots, mountains, and landscapes from financial data.
Uses matplotlib 3D for backend rendering (no browser required).

Renders:
1. Volatility Surface (strike × expiry × IV)
2. Correlation Mountain (asset × asset × correlation)
3. P&L Surface (parameter sweep)
4. Monte Carlo Path Mountain
5. Risk Landscape (VaR across scenarios)
6. Order Book Depth 3D

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.viz.3d")


class Atlas3DRenderer:
    """
    Render 3D financial visualizations to image files.
    """

    def __init__(self, output_dir: str = "data/renders/3d"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _setup_3d(self):
        """Setup matplotlib with 3D backend."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
        return plt

    # ──────────────────────────────────────────────────────────
    # 1. VOLATILITY SURFACE
    # ──────────────────────────────────────────────────────────

    def volatility_surface(
        self,
        strikes: np.ndarray,
        expiries: np.ndarray,
        iv_matrix: np.ndarray,
        title: str = "Implied Volatility Surface",
        filename: str = "vol_surface_3d.png",
        current_price: Optional[float] = None,
    ) -> str:
        """
        3D surface of implied volatility across strikes and expiries.

        Args:
            strikes:   1D array of strike prices
            expiries:  1D array of days to expiration
            iv_matrix: 2D array (strikes × expiries) of IV values
            current_price: Optional ATM marker
        """
        plt = self._setup_3d()
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection="3d")

        X, Y = np.meshgrid(expiries, strikes)
        surf = ax.plot_surface(X, Y, iv_matrix, cmap="magma", alpha=0.85,
                               edgecolors="gray", linewidth=0.2)

        ax.set_xlabel("Days to Expiry", fontsize=11)
        ax.set_ylabel("Strike Price ($)", fontsize=11)
        ax.set_zlabel("Implied Volatility", fontsize=11)
        ax.set_title(title, fontsize=14, pad=20)

        # ATM line
        if current_price is not None:
            ax.plot([expiries.min(), expiries.max()],
                    [current_price, current_price],
                    [iv_matrix.min(), iv_matrix.min()],
                    color="red", linewidth=2, label="ATM")

        fig.colorbar(surf, shrink=0.5, aspect=10, label="IV")
        ax.view_init(elev=30, azim=45)

        path = self.output_dir / filename
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("3D Vol Surface: %s", path)
        return str(path)

    # ──────────────────────────────────────────────────────────
    # 2. CORRELATION MOUNTAIN
    # ──────────────────────────────────────────────────────────

    def correlation_mountain(
        self,
        corr_matrix: pd.DataFrame,
        title: str = "Correlation Landscape",
        filename: str = "correlation_mountain_3d.png",
    ) -> str:
        """
        3D mountain of pairwise correlations.
        Peaks = high correlation, valleys = low/negative correlation.
        """
        plt = self._setup_3d()
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection="3d")

        n = len(corr_matrix)
        X, Y = np.meshgrid(range(n), range(n))
        Z = corr_matrix.values

        surf = ax.plot_surface(X, Y, Z, cmap="coolwarm", alpha=0.85,
                               edgecolors="gray", linewidth=0.3)

        # Labels
        labels = corr_matrix.columns.tolist()
        ax.set_xticks(range(n))
        ax.set_xticklabels(labels, rotation=45, fontsize=8)
        ax.set_yticks(range(n))
        ax.set_yticklabels(labels, rotation=-45, fontsize=8)
        ax.set_zlabel("Correlation", fontsize=11)
        ax.set_title(title, fontsize=14, pad=20)

        fig.colorbar(surf, shrink=0.5, aspect=10, label="ρ")
        ax.view_init(elev=35, azim=135)

        path = self.output_dir / filename
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("3D Correlation Mountain: %s", path)
        return str(path)

    # ──────────────────────────────────────────────────────────
    # 3. P&L SURFACE (parameter sweep)
    # ──────────────────────────────────────────────────────────

    def pnl_surface(
        self,
        param1_values: np.ndarray,
        param2_values: np.ndarray,
        pnl_matrix: np.ndarray,
        param1_name: str = "Parameter 1",
        param2_name: str = "Parameter 2",
        title: str = "Strategy P&L Surface",
        filename: str = "pnl_surface_3d.png",
    ) -> str:
        """
        3D P&L surface from parameter sweep (e.g., MA periods, thresholds).
        """
        plt = self._setup_3d()
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection="3d")

        X, Y = np.meshgrid(param1_values, param2_values)

        # Color: green for profit, red for loss
        colors = np.where(pnl_matrix > 0, 0.3, 0.7)  # For custom coloring

        surf = ax.plot_surface(X, Y, pnl_matrix, cmap="RdYlGn", alpha=0.85,
                               edgecolors="gray", linewidth=0.2)

        # Zero plane
        ax.plot_surface(X, Y, np.zeros_like(pnl_matrix), alpha=0.1, color="gray")

        ax.set_xlabel(param1_name, fontsize=11)
        ax.set_ylabel(param2_name, fontsize=11)
        ax.set_zlabel("P&L ($)", fontsize=11)
        ax.set_title(title, fontsize=14, pad=20)

        fig.colorbar(surf, shrink=0.5, aspect=10, label="P&L")
        ax.view_init(elev=30, azim=45)

        path = self.output_dir / filename
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("3D P&L Surface: %s", path)
        return str(path)

    # ──────────────────────────────────────────────────────────
    # 4. MONTE CARLO PATH MOUNTAIN
    # ──────────────────────────────────────────────────────────

    def monte_carlo_mountain(
        self,
        paths: np.ndarray,
        title: str = "Monte Carlo Path Density",
        filename: str = "mc_mountain_3d.png",
        n_time_slices: int = 20,
    ) -> str:
        """
        3D mountain showing density of MC paths at each time step.
        X = time, Y = price, Z = density (frequency).
        """
        plt = self._setup_3d()
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection="3d")

        n_paths, n_steps = paths.shape
        step_indices = np.linspace(0, n_steps - 1, n_time_slices, dtype=int)

        # Build density at each time slice
        all_prices = paths[:, step_indices]
        price_min = all_prices.min()
        price_max = all_prices.max()
        n_bins = 40
        price_bins = np.linspace(price_min, price_max, n_bins)

        for i, step in enumerate(step_indices):
            hist, edges = np.histogram(paths[:, step], bins=price_bins, density=True)
            centers = (edges[:-1] + edges[1:]) / 2
            ax.bar(centers, hist, zs=step, zdir="y", alpha=0.5, width=(price_max - price_min) / n_bins * 0.8)

        ax.set_xlabel("Price ($)", fontsize=11)
        ax.set_ylabel("Time Step", fontsize=11)
        ax.set_zlabel("Density", fontsize=11)
        ax.set_title(title, fontsize=14, pad=20)
        ax.view_init(elev=25, azim=60)

        path = self.output_dir / filename
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("3D MC Mountain: %s", path)
        return str(path)

    # ──────────────────────────────────────────────────────────
    # 5. RISK LANDSCAPE
    # ──────────────────────────────────────────────────────────

    def risk_landscape(
        self,
        allocations: np.ndarray,
        returns_axis: np.ndarray,
        risk_matrix: np.ndarray,
        title: str = "Risk Landscape (VaR by Allocation & Return)",
        filename: str = "risk_landscape_3d.png",
    ) -> str:
        """
        3D landscape of risk metrics across portfolio allocations and scenarios.
        """
        plt = self._setup_3d()
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection="3d")

        X, Y = np.meshgrid(allocations, returns_axis)
        surf = ax.plot_surface(X, Y, risk_matrix, cmap="hot_r", alpha=0.85,
                               edgecolors="gray", linewidth=0.2)

        ax.set_xlabel("Equity Allocation %", fontsize=11)
        ax.set_ylabel("Market Return %", fontsize=11)
        ax.set_zlabel("VaR ($)", fontsize=11)
        ax.set_title(title, fontsize=14, pad=20)

        fig.colorbar(surf, shrink=0.5, aspect=10, label="VaR")
        ax.view_init(elev=25, azim=50)

        path = self.output_dir / filename
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("3D Risk Landscape: %s", path)
        return str(path)

    # ──────────────────────────────────────────────────────────
    # 6. ORDER BOOK DEPTH 3D
    # ──────────────────────────────────────────────────────────

    def orderbook_depth_3d(
        self,
        timestamps: List[float],
        bid_levels: List[List[Tuple[float, float]]],  # [(price, qty), ...]
        ask_levels: List[List[Tuple[float, float]]],
        title: str = "Order Book Depth Over Time",
        filename: str = "orderbook_depth_3d.png",
    ) -> str:
        """
        3D visualization of order book depth evolving over time.
        X = price, Y = time, Z = quantity at level.
        """
        plt = self._setup_3d()
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection="3d")

        for i, (ts, bids, asks) in enumerate(zip(timestamps, bid_levels, ask_levels)):
            # Bids (green)
            if bids:
                prices = [b[0] for b in bids]
                qtys = [b[1] for b in bids]
                ax.bar(prices, qtys, zs=i, zdir="y", color="green", alpha=0.3, width=0.5)

            # Asks (red)
            if asks:
                prices = [a[0] for a in asks]
                qtys = [a[1] for a in asks]
                ax.bar(prices, qtys, zs=i, zdir="y", color="red", alpha=0.3, width=0.5)

        ax.set_xlabel("Price", fontsize=11)
        ax.set_ylabel("Time", fontsize=11)
        ax.set_zlabel("Quantity", fontsize=11)
        ax.set_title(title, fontsize=14, pad=20)
        ax.view_init(elev=20, azim=60)

        path = self.output_dir / filename
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("3D Orderbook Depth: %s", path)
        return str(path)
