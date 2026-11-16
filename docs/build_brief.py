"""Build the corrected Brief (.docx) from docs/brief_corregido.md.

Usage: python docs/build_brief.py   (needs: pip install python-docx)
Styled after the original Brief: US Letter, narrow margins, Georgia headings, Calibri body.
"""

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Twips

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "brief_corregido.md"
OUTPUT = HERE / "SafeRest360_Brief_AI_Pitch_Corregido.docx"

PAGE_W, MARGIN = 12240, 760
CONTENT_W = PAGE_W - 2 * MARGIN
GREEN_DARK = RGBColor(0x1F, 0x4E, 0x3D)
GRAY = RGBColor(0x55, 0x5F, 0x5A)
HEADER_FILL, ZEBRA_FILL, SECTION_FILL, BORDER = "D5E8DF", "F4F8F6", "E8F2EE", "B7CFC4"

INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")


def shade(element, fill: str) -> None:
    props = element.get_or_add_tcPr() if element.tag == qn("w:tc") else element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    props.append(shd)


def add_runs(paragraph, text: str, size: float = 10, bold: bool = False, color: RGBColor | None = None) -> None:
    for part in INLINE.split(text):
        if not part:
            continue
        run_bold, italic, mono = bold, False, False
        if part.startswith("**") and part.endswith("**"):
            part, run_bold = part[2:-2], True
        elif part.startswith("`") and part.endswith("`"):
            part, mono = part[1:-1], True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            part, italic = part[1:-1], True
        run = paragraph.add_run(part)
        run.bold, run.italic = run_bold, italic
        run.font.size = Pt(size)
        if mono:
            run.font.name = "Consolas"
            run.font.size = Pt(size - 0.5)
        if color is not None:
            run.font.color.rgb = color


def spacing(paragraph, before: float = 0, after: float = 4, line: float = 1.08) -> None:
    fmt = paragraph.paragraph_format
    fmt.space_before, fmt.space_after, fmt.line_spacing = Pt(before), Pt(after), line


def section_heading(doc, text: str) -> None:
    m = re.match(r"^([A-Z])\.\s+(.*)$", text)
    label = f"{m.group(1)}  {m.group(2).upper()}" if m else text.upper()
    p = doc.add_paragraph()
    spacing(p, before=10, after=4)
    p.paragraph_format.keep_with_next = True
    shade(p._p, SECTION_FILL)
    run = p.add_run(label)
    run.bold = True
    run.font.name = "Georgia"
    run.font.size = Pt(12)
    run.font.color.rgb = GREEN_DARK


def set_cell_borders(table) -> None:
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), BORDER)
        borders.append(el)
    table._tbl.tblPr.append(borders)


def add_table(doc, rows: list[list[str]]) -> None:
    header, body = rows[0], rows[1:]
    ncols = len(header)
    cap = 20 if ncols >= 8 else 60
    weights = []
    for i in range(ncols):
        texts = [re.sub(r"[*`]", "", r[i]) if i < len(r) else "" for r in rows]
        longest_word = max((len(w) for t in texts for w in t.split()), default=1)
        # body cells set the width; long headers may wrap
        body_len = max((len(t) for t in texts[1:]), default=0)
        weights.append(max(longest_word + 2, min(body_len, cap), 5))
    widths = [int(CONTENT_W * w / sum(weights)) for w in weights]
    widths[-1] += CONTENT_W - sum(widths)
    size = 8 if ncols >= 8 else 8.5 if ncols >= 5 else 9

    table = doc.add_table(rows=len(rows), cols=ncols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_cell_borders(table)
    for r, values in enumerate(rows):
        row = table.rows[r]
        if r == 0:
            tr_pr = row._tr.get_or_add_trPr()
            hdr = OxmlElement("w:tblHeader")
            hdr.set(qn("w:val"), "true")
            tr_pr.append(hdr)
        for c in range(ncols):
            cell = row.cells[c]
            cell.width = Twips(widths[c])
            if r == 0:
                shade(cell._tc, HEADER_FILL)
            elif r % 2 == 0:
                shade(cell._tc, ZEBRA_FILL)
            p = cell.paragraphs[0]
            spacing(p, after=0, line=1.0)
            add_runs(p, values[c] if c < len(values) else "", size=size, bold=(r == 0))
    spacer = doc.add_paragraph()
    spacing(spacer, after=2)


def parse_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def build() -> Path:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Twips(PAGE_W), Twips(15840)
    sec.left_margin = sec.right_margin = Twips(MARGIN)
    sec.top_margin, sec.bottom_margin = Twips(620), Twips(560)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    normal.font.size = Pt(10)

    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_runs(footer, "SafeRest 360 · Brief corregido · AI Pitch 2026", size=8, color=GRAY)

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped or stripped == "---":
            i += 1
            continue

        if stripped.startswith("# "):
            p = doc.add_paragraph()
            spacing(p, after=2)
            run = p.add_run(stripped[2:].replace(" — versión corregida", ""))
            run.bold, run.font.name, run.font.size = True, "Georgia", Pt(20)
            run.font.color.rgb = GREEN_DARK
            sub = doc.add_paragraph()
            spacing(sub, after=2)
            add_runs(sub, "Versión corregida tras las observaciones del jurado", size=11, bold=True, color=GRAY)
        elif stripped.startswith("## "):
            section_heading(doc, stripped[3:])
        elif stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|$", lines[i].strip()):
                    rows.append(parse_row(lines[i]))
                i += 1
            add_table(doc, rows)
            continue
        elif re.match(r"^\d+\.\s", stripped):
            num, text = stripped.split(" ", 1)
            p = doc.add_paragraph()
            spacing(p, after=2)
            p.paragraph_format.left_indent = Twips(300)
            p.paragraph_format.first_line_indent = Twips(-300)
            add_runs(p, f"{num}\t{text}")
            p.paragraph_format.tab_stops.add_tab_stop(Twips(300))
        elif stripped.startswith("- "):
            p = doc.add_paragraph()
            spacing(p, after=2)
            p.paragraph_format.left_indent = Twips(300)
            p.paragraph_format.first_line_indent = Twips(-200)
            add_runs(p, "•  " + stripped[2:])
        elif stripped.startswith("*[") and stripped.endswith("]*"):
            p = doc.add_paragraph()
            spacing(p, after=4)
            add_runs(p, stripped[1:-1], size=9, color=GRAY)
            for run in p.runs:
                run.italic = True
        else:
            p = doc.add_paragraph()
            spacing(p, after=5)
            if line.startswith("**Universidad"):
                add_runs(p, stripped, size=10, color=GRAY)
            else:
                add_runs(p, stripped)
        i += 1

    doc.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(build())
    sys.exit(0)
