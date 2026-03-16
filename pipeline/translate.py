# Translate non-English title and snippet to English so clustering and output are in English.
# Uses langdetect + deep-translator (Google). Optional: if deps missing, pass-through.
# Optional parallel translation (max_workers) for speed when processing many items.
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from models.normalized import NormalizedItem

_DEPS_AVAILABLE: Optional[bool] = None


def _check_deps() -> bool:
    global _DEPS_AVAILABLE
    if _DEPS_AVAILABLE is not None:
        return _DEPS_AVAILABLE
    try:
        import langdetect  # noqa: F401
        from deep_translator import GoogleTranslator  # noqa: F401
        _DEPS_AVAILABLE = True
    except ImportError:
        _DEPS_AVAILABLE = False
    return _DEPS_AVAILABLE


def _is_ascii_only(text: str) -> bool:
    """True if text is ASCII-only (no accented chars). Skip langdetect/translate for these to speed up."""
    if not text:
        return True
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _detect_lang(text: str) -> str:
    """Return ISO 639-1 code (e.g. 'en', 'es'). Default 'en' if empty or detect fails."""
    if not (text or "").strip():
        return "en"
    try:
        import langdetect
        return langdetect.detect(text) or "en"
    except Exception:
        return "en"


def _translate_to_english(text: str, max_len: int = 2000) -> Optional[str]:
    """Translate text to English. Returns None on failure or if empty."""
    text = (text or "").strip()
    if not text:
        return None
    text = text[:max_len]
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="auto", target="en").translate(text)
    except Exception:
        return None


def _translate_one_item(item: NormalizedItem) -> NormalizedItem:
    """Translate a single item (for parallel execution). Preserves order by index in caller."""
    title = item.title or ""
    body = item.body_or_snippet or ""
    title_en = item.title_en
    body_en = item.body_en

    # Titles: always run langdetect — they are short (<1ms) and ASCII-only is not a reliable
    # proxy for English (Spanish, Italian, French titles are often all-ASCII).
    if not title_en and title:
        lang = _detect_lang(title)
        if lang != "en":
            title_en = _translate_to_english(title, max_len=500)
        else:
            title_en = title

    # Bodies: keep the ASCII bypass — bodies are long and the speed saving matters.
    # If title was detected as non-English, treat body the same way without re-detecting.
    if not body_en and body:
        if _is_ascii_only(body):
            body_en = body
        else:
            # Re-use title language if available; otherwise detect on body
            title_lang = _detect_lang(title) if title else "en"
            lang = title_lang if title else _detect_lang(body)
            if lang != "en":
                body_en = _translate_to_english(body, max_len=1500)
            else:
                body_en = body

    return NormalizedItem(
        id=item.id,
        source_id=item.source_id,
        url=item.url,
        title=item.title,
        body_or_snippet=item.body_or_snippet,
        published_at=item.published_at,
        raw_id=item.raw_id,
        retrieved_at=item.retrieved_at,
        title_en=title_en or item.title_en,
        body_en=body_en or item.body_en,
    )


def translate_to_english(
    normalized_items: List[NormalizedItem],
    max_workers: Optional[int] = 4,
) -> List[NormalizedItem]:
    """
    For each item: detect language; if not English, set title_en and body_en (translated).
    Returns new list of NormalizedItem with title_en/body_en set where translation succeeded.
    If max_workers > 1, translates items in parallel (faster; same results). Set max_workers=1 to disable.
    """
    if not _check_deps():
        return list(normalized_items)
    if not normalized_items:
        return []
    if max_workers is None or max_workers <= 1:
        return [_translate_one_item(item) for item in normalized_items]
    out: List[NormalizedItem] = [None] * len(normalized_items)  # type: ignore[list-item]
    with ThreadPoolExecutor(max_workers=min(max_workers, len(normalized_items))) as executor:
        futures = {executor.submit(_translate_one_item, item): i for i, item in enumerate(normalized_items)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                out[idx] = future.result()
            except Exception:
                out[idx] = _translate_one_item(normalized_items[idx])
    return list(out)
