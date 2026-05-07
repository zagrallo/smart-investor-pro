import json
import logging

logger = logging.getLogger(__name__)


def extract_json(text: str) -> str:
    """Extract valid JSON from LLM responses that may contain markdown or chatter."""
    match = __import__("re").search(r"```json\s*(.*?)\s*```", text, __import__("re").DOTALL)
    if match:
        return match.group(1)
    match = __import__("re").search(r"\{.*\}", text, __import__("re").DOTALL)
    return match.group(0) if match else text


def parse_with_recovery(content: str, model_class):
    """Try multiple strategies to parse JSON into a Pydantic model."""
    if not content or not isinstance(content, str):
        return None

    # Strategy 1: Direct parse
    try:
        return model_class.model_validate_json(content)
    except Exception:
        pass

    # Strategy 2: Extract JSON from markdown or wrapped text
    try:
        clean = extract_json(content)
        return model_class.model_validate_json(clean)
    except Exception as e:
        logger.warning("JSON extraction failed: %s", e)

    # Strategy 3: Find JSON in nested braces
    try:
        depth = 0
        start = end = -1
        for i, c in enumerate(content):
            if c == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0 and start >= 0:
                    end = i + 1
                    break
        if start >= 0 and end > start:
            return model_class.model_validate_json(content[start:end])
    except Exception:
        pass

    return None
