"""FinBERT sentiment analysis with fallback."""

import logging

from src.core.config import settings

logger = logging.getLogger(__name__)

# Lazy-loaded pipeline
_sentiment_pipeline = None


def get_sentiment_pipeline():
    """Lazy load sentiment pipeline."""
    global _sentiment_pipeline

    if _sentiment_pipeline is None:
        if settings.ENABLE_FINBERT:
            try:
                from transformers import pipeline

                logger.info("Loading FinBERT sentiment model...")
                _sentiment_pipeline = pipeline(
                    "sentiment-analysis", model="ProsusAI/finbert", device=-1  # CPU
                )
                logger.info("FinBERT model loaded successfully")
            except ImportError:
                logger.warning(
                    "transformers package not installed. Install with: pip install torch transformers"
                )
                _sentiment_pipeline = None
            except Exception as e:
                logger.error(f"Failed to load FinBERT model: {e}")
                _sentiment_pipeline = None
        else:
            logger.info("FinBERT disabled via config")
            _sentiment_pipeline = None

    return _sentiment_pipeline


def analyze_sentiment(text: str) -> dict[str, float]:
    """Analyze sentiment of text.

    Args:
        text: Input text to analyze

    Returns:
        Dictionary with keys: sent_pos, sent_neg, sent_comp
    """
    pipeline = get_sentiment_pipeline()

    if pipeline is None or not settings.ENABLE_FINBERT:
        # Fallback: return neutral sentiment
        return {"sent_pos": 0.0, "sent_neg": 0.0, "sent_comp": 0.0}

    try:
        # Truncate text to avoid token limits
        text = text[:512]

        result = pipeline(text)[0]
        label = result["label"].lower()
        score = result["score"]

        # Map FinBERT labels to our schema
        sent_pos = 0.0
        sent_neg = 0.0
        sent_comp = 0.0

        if label == "positive":
            sent_pos = score
            sent_comp = score
        elif label == "negative":
            sent_neg = score
            sent_comp = -score
        else:  # neutral
            sent_comp = 0.0

        return {"sent_pos": sent_pos, "sent_neg": sent_neg, "sent_comp": sent_comp}

    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        # Return neutral on error
        return {"sent_pos": 0.0, "sent_neg": 0.0, "sent_comp": 0.0}


def analyze_batch_sentiment(texts: list[str]) -> list[dict[str, float]]:
    """Analyze sentiment for a batch of texts.

    Args:
        texts: List of texts to analyze

    Returns:
        List of sentiment dictionaries
    """
    return [analyze_sentiment(text) for text in texts]
