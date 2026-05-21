import re
import unicodedata

def slugify(text: str) -> str:
    """
    Convert a string into a clean, URL-friendly slug.
    Normalizes unicode, converts to lowercase, removes non-alphanumeric characters,
    and replaces whitespace/hyphens with a single hyphen.
    """
    if not text:
        return ""
    # Normalize unicode (normalize accented characters, e.g., é -> e)
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    # Lowercase
    text = text.lower()
    # Replace anything that isn't a alphanumeric, space, or hyphen with empty string
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    # Replace spaces and consecutive hyphens with a single hyphen
    text = re.sub(r'[\s-]+', '-', text)
    # Strip leading/trailing hyphens
    return text.strip('-')
