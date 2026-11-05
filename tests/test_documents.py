import io

from docx import Document
from pypdf import PdfReader

import documents

RESUME = """# Jane Doe
jane@x.com

## Experience
### Data Engineer, Acme (2021 \u2013 2024)
- Built **ETL pipelines** in Python
- Cut costs by 30% \u2022 saved \u201cmoney\u201d
* Star bullet with --dashes-- and __underscores__

Plain paragraph with **bold** inside.
"""


def test_parse_markdown_kinds():
    kinds = [kind for kind, _ in documents.parse_markdown(RESUME)]
    assert kinds == ["h1", "para", "h2", "h3", "bullet", "bullet", "bullet", "para"]


def test_parse_markdown_caps_heading_depth():
    assert documents.parse_markdown("###### deep") == [("h3", "deep")]


def test_split_bold():
    assert documents.split_bold("a **b** c") == [("a ", False), ("b", True), (" c", False)]


def test_letter_keeps_closing_on_separate_lines():
    blocks = documents.parse_letter("Dear team,\n\nI build things.\n\nThanks,\nJane")
    assert blocks == [("line", "Dear team,"), ("gap", ""), ("line", "I build things."),
                      ("gap", ""), ("line", "Thanks,"), ("line", "Jane")]


def test_docx_structure():
    doc = Document(io.BytesIO(documents.build("resume", "docx", RESUME)))
    assert [(p.style.name, p.text) for p in doc.paragraphs][:2] == [("Heading 1", "Jane Doe"), ("Normal", "jane@x.com")]
    assert [r.text for p in doc.paragraphs for r in p.runs if r.bold] == ["ETL pipelines", "bold"]
    assert "List Bullet" in {p.style.name for p in doc.paragraphs}


def test_pdf_text_and_latin1_fallbacks():
    pdf = PdfReader(io.BytesIO(documents.build("resume", "pdf", RESUME)))
    text = pdf.pages[0].extract_text()
    assert "ETL pipelines" in text
    assert "(2021 - 2024)" in text          # en dash replaced
    assert "--dashes--" in text             # not treated as markdown underline


def test_pdf_survives_awkward_input():
    documents.build("resume", "pdf", "# \u5f20\u4f1f\n- caf\u00e9 \u2192 na\u00efve")
    documents.build("resume", "pdf", "Link: https://example.com/" + "a" * 400)
    documents.build("resume", "pdf", "")
    documents.build("letter", "docx", "")


def test_long_resume_makes_several_pages():
    big = "\n".join(f"- bullet {i} " + "word " * 30 for i in range(120))
    assert len(PdfReader(io.BytesIO(documents.build("resume", "pdf", big))).pages) > 1


def test_unknown_format_raises():
    import pytest
    with pytest.raises(ValueError):
        documents.build("resume", "rtf", "x")
