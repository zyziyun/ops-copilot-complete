from app.rag.multimodal import IMAGE_EXTS, extract_markdown_tables

SAMPLE = """
intro text

| signal | severity | action |
|---|---|---|
| connections > 90% | high | terminate stuck backends |
| disk > 85% | critical | free WAL |

outro text
"""


def test_extract_markdown_tables_keeps_table_whole():
    tables = extract_markdown_tables(SAMPLE)
    assert len(tables) == 1
    assert "severity" in tables[0]
    assert "critical" in tables[0]
    # surrounding prose is not part of the table block
    assert "intro text" not in tables[0]


def test_no_tables_returns_empty():
    assert extract_markdown_tables("just prose, no pipes here") == []


def test_image_exts_cover_common_formats():
    assert {".png", ".jpg", ".jpeg"} <= IMAGE_EXTS
