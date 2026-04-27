"""
HuggingFace Inference API Provider

Provides NLP capabilities: sentiment analysis, financial sentiment analysis,
and text embeddings using HuggingFace models.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import os
from typing import Optional, Dict, List, Any

logger = logging.getLogger("atlas.data_layer.huggingface_provider")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class HuggingFaceProvider:
    """
    Provides NLP and sentiment analysis via HuggingFace Inference API.

    Supports:
    - General sentiment analysis
    - Financial sentiment analysis (using FinBERT)
    - Text embeddings

    Requires HUGGINGFACE_API_KEY environment variable.

    Example::

        provider = HuggingFaceProvider()
        if provider.available:
            sentiment = provider.analyze_sentiment("Great earnings report!")
            fin_sentiment = provider.analyze_financial_sentiment("Fed raises rates")
            embeddings = provider.get_embeddings("Apple stock")
    """

    BASE_URL = "https://api-inference.huggingface.co/models"

    # Model endpoints
    SENTIMENT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"
    FINBERT_MODEL = "ProsusAI/finbert"
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self):
        """Initialize HuggingFace provider with API key from environment"""
        self.available = False
        self.api_key = os.environ.get("HUGGINGFACE_API_KEY")

        if not self.api_key:
            logger.warning("HUGGINGFACE_API_KEY not found in environment")
            return

        if not REQUESTS_AVAILABLE:
            logger.warning("requests not installed. Install with: pip install requests")
            return

        self.available = True
        logger.info("HuggingFace provider initialized")

    def _make_request(
        self,
        model: str,
        inputs: Any,
    ) -> Optional[Any]:
        """
        Make request to HuggingFace Inference API.

        Args:
            model: Model identifier
            inputs: Input data (string or dict)

        Returns:
            Response data or None on failure
        """
        try:
            url = f"{self.BASE_URL}/{model}"
            headers = {"Authorization": f"Bearer {self.api_key}"}

            # Handle different input types
            if isinstance(inputs, str):
                payload = {"inputs": inputs}
            else:
                payload = {"inputs": inputs}

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"HuggingFace API request failed: {e}")
            return None

    def analyze_sentiment(self, text: str) -> Optional[Dict]:
        """
        Analyze general sentiment of text using DistilBERT.

        Args:
            text: Text to analyze

        Returns:
            Dict with keys:
            - label: "POSITIVE" or "NEGATIVE"
            - score: Confidence score (0-1)
            Returns None on failure.

        Example::

            result = provider.analyze_sentiment("This is great news!")
            # Returns:
            # {
            #     "label": "POSITIVE",
            #     "score": 0.9987
            # }
        """
        if not self.available:
            logger.warning("HuggingFace provider not available")
            return None

        try:
            response = self._make_request(self.SENTIMENT_MODEL, text)

            if response is None:
                return None

            # Response is a list of predictions
            if isinstance(response, list) and len(response) > 0:
                predictions = response[0]
                if isinstance(predictions, list) and len(predictions) > 0:
                    # Find the best prediction
                    best = max(predictions, key=lambda x: x.get("score", 0))
                    result = {
                        "label": best.get("label", "NEUTRAL"),
                        "score": float(best.get("score", 0)),
                    }
                    logger.info(f"Sentiment analysis: {result['label']} ({result['score']:.4f})")
                    return result

            logger.warning(f"Unexpected response format: {response}")
            return None

        except Exception as e:
            logger.error(f"Failed to analyze sentiment: {e}")
            return None

    def analyze_financial_sentiment(self, text: str) -> Optional[Dict]:
        """
        Analyze financial sentiment using FinBERT model.

        Better at understanding financial context and nuances.

        Args:
            text: Financial text to analyze

        Returns:
            Dict with keys:
            - label: "positive", "negative", or "neutral"
            - score: Confidence score (0-1)
            Returns None on failure.

        Example::

            result = provider.analyze_financial_sentiment("Earnings missed expectations")
            # Returns:
            # {
            #     "label": "negative",
            #     "score": 0.9234
            # }
        """
        if not self.available:
            logger.warning("HuggingFace provider not available")
            return None

        try:
            response = self._make_request(self.FINBERT_MODEL, text)

            if response is None:
                return None

            # Response is a list of predictions
            if isinstance(response, list) and len(response) > 0:
                predictions = response[0]
                if isinstance(predictions, list) and len(predictions) > 0:
                    # Find the best prediction
                    best = max(predictions, key=lambda x: x.get("score", 0))
                    result = {
                        "label": best.get("label", "neutral").lower(),
                        "score": float(best.get("score", 0)),
                    }
                    logger.info(
                        f"Financial sentiment analysis: {result['label']} "
                        f"({result['score']:.4f})"
                    )
                    return result

            logger.warning(f"Unexpected response format: {response}")
            return None

        except Exception as e:
            logger.error(f"Failed to analyze financial sentiment: {e}")
            return None

    def get_embeddings(self, text: str) -> Optional[List[float]]:
        """
        Get dense embeddings for text using sentence-transformer.

        Returns a 384-dimensional embedding vector.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding.
            Returns None on failure.

        Example::

            embedding = provider.get_embeddings("Apple stock")
            # Returns: [0.1234, -0.5678, ..., 0.9876]  (384 dimensions)
        """
        if not self.available:
            logger.warning("HuggingFace provider not available")
            return None

        try:
            response = self._make_request(self.EMBEDDING_MODEL, text)

            if response is None:
                return None

            # Response should be a list of embeddings
            if isinstance(response, list) and len(response) > 0:
                embedding = response[0]
                if isinstance(embedding, list):
                    logger.info(f"Generated embedding with {len(embedding)} dimensions")
                    return embedding

            logger.warning(f"Unexpected embedding response: {response}")
            return None

        except Exception as e:
            logger.error(f"Failed to get embeddings: {e}")
            return None

    def analyze_similarity(
        self,
        text1: str,
        text2: str,
    ) -> Optional[float]:
        """
        Calculate cosine similarity between two texts using embeddings.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1), or None on failure.
        """
        if not self.available:
            logger.warning("HuggingFace provider not available")
            return None

        try:
            embed1 = self.get_embeddings(text1)
            embed2 = self.get_embeddings(text2)

            if embed1 is None or embed2 is None:
                return None

            # Calculate cosine similarity
            import math

            dot_product = sum(a * b for a, b in zip(embed1, embed2))
            norm1 = math.sqrt(sum(a * a for a in embed1))
            norm2 = math.sqrt(sum(b * b for b in embed2))

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            logger.info(f"Text similarity: {similarity:.4f}")
            return similarity

        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return None

    def batch_sentiment(
        self,
        texts: List[str],
        use_finbert: bool = False,
    ) -> List[Optional[Dict]]:
        """
        Analyze sentiment for multiple texts.

        Args:
            texts: List of texts to analyze
            use_finbert: Use FinBERT (True) or DistilBERT (False)

        Returns:
            List of sentiment dicts, one per text.
        """
        if not self.available:
            logger.warning("HuggingFace provider not available")
            return [None] * len(texts)

        results = []
        for text in texts:
            if use_finbert:
                result = self.analyze_financial_sentiment(text)
            else:
                result = self.analyze_sentiment(text)
            results.append(result)

        logger.info(f"Analyzed {len(results)} texts")
        return results

    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "name": "HuggingFace",
            "available": self.available,
            "api_key_set": bool(self.api_key),
            "library_available": REQUESTS_AVAILABLE,
            "models": {
                "sentiment": self.SENTIMENT_MODEL,
                "finbert": self.FINBERT_MODEL,
                "embeddings": self.EMBEDDING_MODEL,
            },
            "features": [
                "General sentiment analysis",
                "Financial sentiment analysis",
                "Text embeddings",
                "Text similarity",
            ],
        }
