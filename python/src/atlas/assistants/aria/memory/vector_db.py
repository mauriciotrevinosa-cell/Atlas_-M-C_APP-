"""
ARIA Vector Memory - Production-grade embeddings and semantic search.

Supports dual backends:
- LocalVectorStore: Pure numpy implementation, no external dependencies
- ChromaDBStore: Optional production vector database using chromadb

Copyright (c) 2026 M&C. All rights reserved.
"""

import json
import logging
import math
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np

logger = logging.getLogger("atlas.aria.memory.vector_db")

# Optional dependencies
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


@dataclass
class VectorEntry:
    """Entry in vector store."""
    id: str
    text: str
    embedding: List[float]
    metadata: Optional[Dict] = None


class EmbeddingProvider:
    """Provides embeddings using available models."""

    def __init__(self):
        """Initialize embedding provider with available models."""
        self.model = None
        self.available = False
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the best available embedding model."""
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                self.available = True
                logger.info("Initialized SentenceTransformer for embeddings")
            except Exception as e:
                logger.warning(f"Failed to initialize SentenceTransformer: {e}")
                self.model = None
                self.available = False

    def embed(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text.

        Falls back to TF-IDF if sentence-transformers unavailable.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats, or None on failure
        """
        if not text or not isinstance(text, str):
            return None

        if SENTENCE_TRANSFORMERS_AVAILABLE and self.model:
            try:
                embedding = self.model.encode(text, convert_to_numpy=True)
                return embedding.tolist()
            except Exception as e:
                logger.error(f"Failed to embed text: {e}")
                return None

        # Fallback: simple TF-IDF-inspired embedding
        return self._tfidf_embed(text)

    @staticmethod
    def _tfidf_embed(text: str, dim: int = 384) -> List[float]:
        """
        Generate simple TF-IDF-style embedding (fallback).

        Creates a fixed-dimension embedding based on character frequencies.

        Args:
            text: Text to embed
            dim: Embedding dimension

        Returns:
            Fixed-dimension embedding vector
        """
        text_lower = text.lower()
        char_freq = {}

        for char in text_lower:
            if char.isalnum():
                char_freq[char] = char_freq.get(char, 0) + 1

        # Normalize
        total = sum(char_freq.values()) or 1
        normalized = {k: v / total for k, v in char_freq.items()}

        # Create fixed-dimension vector using hash-based mapping
        embedding = [0.0] * dim
        for char, freq in normalized.items():
            idx = abs(hash(char)) % dim
            embedding[idx] += freq

        # Normalize vector
        norm = math.sqrt(sum(x * x for x in embedding)) or 1.0
        embedding = [x / norm for x in embedding]

        return embedding


class VectorStoreBackend(ABC):
    """Abstract base for vector store backends."""

    @abstractmethod
    def add(self, text: str, metadata: Optional[Dict] = None,
            embedding: Optional[List[float]] = None) -> str:
        """Add text with optional embedding and metadata."""
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5,
               metadata_filter: Optional[Dict] = None) -> List[Tuple[VectorEntry, float]]:
        """Search for similar texts. Returns (entry, score) tuples."""
        pass

    @abstractmethod
    def delete(self, entry_id: str) -> bool:
        """Delete entry by ID."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Count stored entries."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries."""
        pass


class LocalVectorStore(VectorStoreBackend):
    """Pure numpy vector store with JSON persistence."""

    def __init__(self, persist_path: str = "data/aria_vectors.json"):
        """
        Initialize local vector store.

        Args:
            persist_path: Path to JSON file for persistence
        """
        self.persist_path = Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedder = EmbeddingProvider()
        self.entries: Dict[str, VectorEntry] = {}
        self.lock = threading.Lock()
        self._load_from_disk()

    def add(self, text: str, metadata: Optional[Dict] = None,
            embedding: Optional[List[float]] = None) -> str:
        """
        Add text to vector store.

        Args:
            text: Text to store
            metadata: Optional metadata dict
            embedding: Optional pre-computed embedding

        Returns:
            Entry ID
        """
        entry_id = str(uuid4())

        if embedding is None:
            embedding = self.embedder.embed(text)

        if embedding is None:
            logger.warning(f"Failed to generate embedding for text: {text[:50]}...")
            embedding = [0.0] * 384

        with self.lock:
            self.entries[entry_id] = VectorEntry(
                id=entry_id,
                text=text,
                embedding=embedding,
                metadata=metadata or {}
            )
            self._persist()

        logger.debug(f"Added vector entry {entry_id}")
        return entry_id

    def search(self, query: str, top_k: int = 5,
               metadata_filter: Optional[Dict] = None) -> List[Tuple[VectorEntry, float]]:
        """
        Search for similar texts using cosine similarity.

        Args:
            query: Query text
            top_k: Number of results to return
            metadata_filter: Filter by metadata fields (e.g., {"type": "market_data"})

        Returns:
            List of (VectorEntry, similarity_score) tuples
        """
        query_embedding = self.embedder.embed(query)
        if query_embedding is None:
            logger.warning("Failed to embed query")
            return []

        with self.lock:
            candidates = self.entries.values()

        # Filter by metadata if provided
        if metadata_filter:
            candidates = [
                e for e in candidates
                if all(e.metadata.get(k) == v for k, v in metadata_filter.items())
            ]

        # Calculate similarities
        similarities = []
        for entry in candidates:
            score = self._cosine_similarity(query_embedding, entry.embedding)
            similarities.append((entry, score))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def delete(self, entry_id: str) -> bool:
        """Delete entry by ID."""
        with self.lock:
            if entry_id in self.entries:
                del self.entries[entry_id]
                self._persist()
                logger.debug(f"Deleted vector entry {entry_id}")
                return True
        return False

    def count(self) -> int:
        """Get number of stored entries."""
        return len(self.entries)

    def clear(self) -> None:
        """Clear all entries."""
        with self.lock:
            self.entries.clear()
            self._persist()
            logger.info("Cleared all vector entries")

    def _persist(self) -> None:
        """Save entries to disk as JSON."""
        try:
            data = {
                entry_id: {
                    "text": entry.text,
                    "embedding": entry.embedding,
                    "metadata": entry.metadata,
                }
                for entry_id, entry in self.entries.items()
            }
            with open(self.persist_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist vectors: {e}")

    def _load_from_disk(self) -> None:
        """Load entries from disk JSON."""
        if not self.persist_path.exists():
            return

        try:
            with open(self.persist_path, "r") as f:
                data = json.load(f)

            for entry_id, entry_data in data.items():
                self.entries[entry_id] = VectorEntry(
                    id=entry_id,
                    text=entry_data["text"],
                    embedding=entry_data["embedding"],
                    metadata=entry_data.get("metadata", {}),
                )
            logger.info(f"Loaded {len(self.entries)} vector entries from disk")
        except Exception as e:
            logger.error(f"Failed to load vectors from disk: {e}")

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


class ChromaDBStore(VectorStoreBackend):
    """ChromaDB-based vector store for production use."""

    def __init__(self, collection_name: str = "aria_memory",
                 persist_dir: str = "data/chroma_db"):
        """
        Initialize ChromaDB store.

        Args:
            collection_name: Name of ChromaDB collection
            persist_dir: Directory for ChromaDB persistence
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("chromadb not installed. Install with: pip install chromadb")

        self.embedder = EmbeddingProvider()
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self.lock = threading.Lock()
        logger.info(f"Initialized ChromaDB store: {collection_name}")

    def add(self, text: str, metadata: Optional[Dict] = None,
            embedding: Optional[List[float]] = None) -> str:
        """Add text to ChromaDB."""
        entry_id = str(uuid4())

        if embedding is None:
            embedding = self.embedder.embed(text)

        if embedding is None:
            logger.warning(f"Failed to generate embedding: {text[:50]}...")
            return entry_id

        with self.lock:
            self.collection.add(
                ids=[entry_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata or {}]
            )

        logger.debug(f"Added to ChromaDB: {entry_id}")
        return entry_id

    def search(self, query: str, top_k: int = 5,
               metadata_filter: Optional[Dict] = None) -> List[Tuple[VectorEntry, float]]:
        """Search ChromaDB collection."""
        query_embedding = self.embedder.embed(query)
        if query_embedding is None:
            logger.warning("Failed to embed query")
            return []

        with self.lock:
            where = metadata_filter if metadata_filter else None
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where
            )

        entries = []
        if results and results["documents"] and len(results["documents"]) > 0:
            for i, doc in enumerate(results["documents"][0]):
                entry_id = results["ids"][0][i]
                distance = results["distances"][0][i]
                # ChromaDB distance is 1 - cosine_similarity
                similarity = 1 - distance
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}

                entry = VectorEntry(
                    id=entry_id,
                    text=doc,
                    embedding=results["embeddings"][0][i] if results["embeddings"] else [],
                    metadata=metadata
                )
                entries.append((entry, similarity))

        return entries

    def delete(self, entry_id: str) -> bool:
        """Delete entry from ChromaDB."""
        try:
            with self.lock:
                self.collection.delete(ids=[entry_id])
            logger.debug(f"Deleted from ChromaDB: {entry_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from ChromaDB: {e}")
            return False

    def count(self) -> int:
        """Get count of entries in collection."""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Failed to get collection count: {e}")
            return 0

    def clear(self) -> None:
        """Clear all entries from collection."""
        try:
            with self.lock:
                # Delete collection and recreate
                self.client.delete_collection(name=self.collection.name)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection.name,
                    metadata={"hnsw:space": "cosine"}
                )
            logger.info("Cleared ChromaDB collection")
        except Exception as e:
            logger.error(f"Failed to clear ChromaDB: {e}")


class VectorMemory:
    """
    Production-grade vector memory for ARIA.

    Supports dual backends: LocalVectorStore (default) and ChromaDBStore (optional).
    Handles embeddings, semantic search, and metadata filtering.

    Example::

        # Use local store (default)
        memory = VectorMemory.create(backend="local")
        entry_id = memory.add("Apple stock price increased",
                              metadata={"type": "market_data", "ticker": "AAPL"})

        results = memory.search("stock price movement", top_k=5)
        results = memory.search("apple", metadata_filter={"ticker": "AAPL"})

        # Or use ChromaDB for production
        memory = VectorMemory.create(backend="chromadb")
    """

    def __init__(self, backend: VectorStoreBackend):
        """
        Initialize VectorMemory with backend.

        Args:
            backend: VectorStoreBackend instance (LocalVectorStore or ChromaDBStore)
        """
        self.backend = backend
        self.available = True

    @classmethod
    def create(cls, backend: str = "local", **kwargs) -> "VectorMemory":
        """
        Factory method to create VectorMemory with specified backend.

        Args:
            backend: "local" for LocalVectorStore, "chromadb" for ChromaDBStore
            **kwargs: Additional arguments passed to backend constructor

        Returns:
            VectorMemory instance

        Raises:
            ValueError: If backend is not recognized or unavailable
        """
        if backend == "local":
            store = LocalVectorStore(**kwargs)
            logger.info("Created VectorMemory with LocalVectorStore backend")
            return cls(store)

        elif backend == "chromadb":
            if not CHROMADB_AVAILABLE:
                raise ValueError(
                    "chromadb backend requested but not installed. "
                    "Install with: pip install chromadb"
                )
            store = ChromaDBStore(**kwargs)
            logger.info("Created VectorMemory with ChromaDBStore backend")
            return cls(store)

        else:
            raise ValueError(f"Unknown backend: {backend}")

    def add(self, text: str, metadata: Optional[Dict] = None,
            embedding: Optional[List[float]] = None) -> str:
        """
        Add text to vector memory.

        Args:
            text: Text to store
            metadata: Optional metadata dict for filtering
            embedding: Optional pre-computed embedding

        Returns:
            Entry ID
        """
        return self.backend.add(text, metadata, embedding)

    def search(self, query: str, top_k: int = 5,
               metadata_filter: Optional[Dict] = None) -> List[Tuple[VectorEntry, float]]:
        """
        Search vector memory for similar texts.

        Args:
            query: Query text
            top_k: Number of results to return
            metadata_filter: Filter by metadata fields

        Returns:
            List of (VectorEntry, similarity_score) tuples sorted by relevance
        """
        return self.backend.search(query, top_k, metadata_filter)

    def delete(self, entry_id: str) -> bool:
        """Delete entry by ID."""
        return self.backend.delete(entry_id)

    def count(self) -> int:
        """Get number of stored entries."""
        return self.backend.count()

    def clear(self) -> None:
        """Clear all entries."""
        self.backend.clear()

    def get_info(self) -> Dict:
        """Get memory info."""
        return {
            "backend": type(self.backend).__name__,
            "available": self.available,
            "entry_count": self.count(),
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2" if SENTENCE_TRANSFORMERS_AVAILABLE else "TF-IDF fallback",
            "chromadb_available": CHROMADB_AVAILABLE,
        }
