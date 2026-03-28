import os

RULES_PATH = os.path.join(os.path.dirname(__file__), "nyc_rules.txt")

# Gemini 3 supports ~1M tokens, so we default to one clean context block.
# The chunk helper exists only as a fallback for future rule expansions.
CHUNK_SIZE_CHARS = 800_000


def load_rules() -> str:
    """Load the full NYC compliance rules as a single context string."""
    if not os.path.exists(RULES_PATH):
        return ""
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return f.read()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS) -> list[str]:
    """Split text into chunks only when it exceeds chunk_size characters."""
    if len(text) <= chunk_size:
        return [text]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def get_context_block() -> str:
    """Return rules as a single block; falls back to first chunk if enormous."""
    rules = load_rules()
    chunks = chunk_text(rules)
    return chunks[0] if chunks else ""
