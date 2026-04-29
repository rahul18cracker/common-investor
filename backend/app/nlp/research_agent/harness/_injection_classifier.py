"""Lazy-loaded DeBERTa-based prompt injection classifier.

Wraps the protectai/deberta-v3-base-prompt-injection-v2 model to detect
prompt injection attempts. Gracefully degrades if transformers is unavailable.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_pipeline = None


def classify_injection(text: str) -> tuple[float, str]:
    """
    Classify text as injection or benign.

    Args:
        text: Input text to classify.

    Returns:
        tuple: (confidence_score: float, label: str)
               score is 0.0-1.0, label is 'injection' or 'benign'.
               Returns (0.0, 'benign') if model fails to load.
    """
    global _pipeline

    # Lazy load on first call
    if _pipeline is None:
        try:
            from transformers import pipeline  # type: ignore

            _pipeline = pipeline(
                "text-classification",
                model="protectai/deberta-v3-base-prompt-injection-v2",
                truncation=True,
                max_length=512,
            )
            logger.info("DeBERTa injection classifier loaded successfully")
        except ImportError:
            logger.warning("transformers not available; T2 injection detection disabled")
            _pipeline = False
        except Exception as e:
            logger.error(f"Failed to load DeBERTa model: {e}; T2 detection disabled")
            _pipeline = False

    # If load failed, return benign (degrade gracefully)
    if _pipeline is False:
        return 0.0, "benign"

    try:
        result = _pipeline(text, truncation=True, max_length=512)
        if not result:
            return 0.0, "benign"

        # result is a list of dicts like [{'label': 'injection', 'score': 0.95}]
        item = result[0]
        label = item.get("label", "benign").lower()
        score = float(item.get("score", 0.0))

        return score, label
    except Exception as e:
        logger.error(f"DeBERTa inference error: {e}")
        return 0.0, "benign"
