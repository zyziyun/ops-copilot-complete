"""Turn a source file into typed ingestion units, one per modality.

- markdown/text → ``text`` chunks, plus any markdown ``table`` blocks kept whole
- pdf            → extracted ``text`` chunks (pypdf)
- image          → a single ``image`` unit whose content is a vision-model caption

Each unit is ``{"content": str, "modality": "text"|"table"|"image"}``; the caller
embeds ``content`` like any other chunk, so images and tables become first-class
search hits.
"""
import base64
from pathlib import Path

from app.clients import aclient
from app.config import settings
from app.rag.ingest import chunk_text

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def extract_pdf_text(path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_markdown_tables(text: str) -> list[str]:
    """Pull out contiguous markdown table blocks so they survive chunking intact."""
    tables: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.count("|") >= 2:
            current.append(line)
        else:
            if len(current) >= 2:  # header + at least one row/separator
                tables.append("\n".join(current))
            current = []
    if len(current) >= 2:
        tables.append("\n".join(current))
    return tables


async def caption_image(path: str) -> str:
    """Caption an image with the vision model so it is searchable as text."""
    data = base64.b64encode(Path(path).read_bytes()).decode()
    ext = Path(path).suffix.lstrip(".").lower() or "png"
    resp = await aclient.chat.completions.create(
        model=settings.chat_model,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Describe this image for an ops runbook search index. "
                            "Be specific about any diagrams, metrics, errors, "
                            "dashboards, or UI shown."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/{ext};base64,{data}"},
                    },
                ],
            }
        ],
    )
    return resp.choices[0].message.content


async def build_units(path: str, body: str) -> list[dict]:
    """Return typed units for a file. ``body`` is the front-matter-stripped text
    for markdown/text inputs (ignored for pdf/image)."""
    suffix = Path(path).suffix.lower()

    if suffix in IMAGE_EXTS:
        return [{"content": await caption_image(path), "modality": "image"}]

    if suffix == ".pdf":
        text = extract_pdf_text(path)
        return [{"content": c, "modality": "text"} for c in chunk_text(text)]

    # markdown / text: text chunks + any tables kept whole
    units = [{"content": c, "modality": "text"} for c in chunk_text(body)]
    units += [{"content": t, "modality": "table"} for t in extract_markdown_tables(body)]
    return units
