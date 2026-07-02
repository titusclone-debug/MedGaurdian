"""Public-facing NABH text helpers.

The canonical corpus stores official text internally for provenance. Under the
Option B governance model, API/UI responses must not display that text
verbatim unless a source document explicitly allows display.
"""

from typing import Optional


REDACTION_NOTICE = (
    "Official NABH text is stored internally for provenance and is not displayed "
    "verbatim. Use the requirement code and cited locator for source verification."
)


def can_display_full_text(source_document: Optional[object] = None) -> bool:
    return bool(
        source_document is not None
        and getattr(source_document, "may_display_full_text", False) is True
    )


def requirement_public_text(requirement: object, source_document: Optional[object] = None) -> str:
    if can_display_full_text(source_document):
        return getattr(requirement, "display_text", "") or REDACTION_NOTICE
    code = getattr(requirement, "canonical_code", None) or getattr(requirement, "official_code", None)
    if code:
        return f"{code}: {REDACTION_NOTICE}"
    return REDACTION_NOTICE


def redact_source_heading(source_document: Optional[object] = None, source_heading: Optional[str] = None) -> Optional[str]:
    if can_display_full_text(source_document):
        return source_heading
    return None
