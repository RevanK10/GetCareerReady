import io
import re

from docx import Document
from docx.shared import Pt
from fpdf import FPDF

REPLACEMENTS = {
    "\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2022": "-", "\u2026": "...", "\u00a0": " ",
}


def parse_markdown(md):
    """Turn simple Markdown into (kind, text) blocks: h1-h3, bullet, para."""
    blocks = []
    for line in md.splitlines():
        if not line.strip():
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)", line)
        bullet = re.match(r"^\s*[-*\u2022]\s+(.*)", line)
        if heading:
            blocks.append((f"h{min(len(heading.group(1)), 3)}", heading.group(2).strip()))
        elif bullet:
            blocks.append(("bullet", bullet.group(1).strip()))
        else:
            blocks.append(("para", line.strip()))
    return blocks


def parse_letter(text):
    """Keep a letter's line breaks (salutation, closing), and mark blank lines as gaps."""
    blocks = []
    for line in text.strip().splitlines():
        blocks.append(("line", line.strip()) if line.strip() else ("gap", ""))
    return blocks


def split_bold(text):
    """'a **b** c' -> [('a ', False), ('b', True), (' c', False)]"""
    parts = re.split(r"\*\*(.+?)\*\*", text)
    return [(chunk, i % 2 == 1) for i, chunk in enumerate(parts) if chunk]


def strip_bold(text):
    return text.replace("**", "")


def render_docx(blocks):
    doc = Document()
    for kind, text in blocks:
        if kind.startswith("h"):
            doc.add_heading(strip_bold(text), level=int(kind[1]))
        elif kind == "gap":
            doc.add_paragraph("")
        elif kind == "line":
            doc.add_paragraph(text).paragraph_format.space_after = Pt(0)
        else:
            paragraph = doc.add_paragraph(style="List Bullet" if kind == "bullet" else None)
            for chunk, bold in split_bold(text):
                paragraph.add_run(chunk).bold = bold
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def to_latin1(text):
    """The built-in PDF fonts only know Latin-1, so swap common symbols and replace the rest."""
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def render_pdf(blocks):
    pdf = FPDF(format="Letter")
    pdf.set_margins(18, 16, 18)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    sizes = {"h1": 18, "h2": 13, "h3": 11}

    for kind, text in blocks:
        text = to_latin1(text)
        if kind == "gap":
            pdf.ln(5.5)
            continue
        if kind in sizes:
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", sizes[kind])
            pdf.multi_cell(0, 7, strip_bold(text), new_x="LMARGIN", new_y="NEXT")
            continue

        indent = 5 if kind == "bullet" else 0
        pdf.l_margin += indent
        pdf.set_x(pdf.l_margin)
        if kind == "bullet":
            text = "- " + text
        for chunk, bold in split_bold(text):
            pdf.set_font("Helvetica", "B" if bold else "", 10.5)
            pdf.write(5.5, chunk)
        pdf.ln(7 if kind == "para" else 5.5)  # a bullet or letter line is tighter than a paragraph
        pdf.l_margin -= indent
        pdf.set_x(pdf.l_margin)
    return bytes(pdf.output())


def build(kind, fmt, text):
    """kind: 'resume' or 'letter'. fmt: 'docx' or 'pdf'. Returns the file as bytes."""
    blocks = parse_markdown(text) if kind == "resume" else parse_letter(text)
    if fmt == "docx":
        return render_docx(blocks)
    if fmt == "pdf":
        return render_pdf(blocks)
    raise ValueError(f"Unknown format: {fmt}")