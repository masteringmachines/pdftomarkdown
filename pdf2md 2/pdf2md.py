"""
pdf2md.py — Convert any PDF to clean Markdown.

Handles:
  • Digital PDFs  (text-based, fast path via pdfplumber)
  • Scanned PDFs  (image-based, OCR via pytesseract)
  • Tables        → Markdown pipe tables
  • Headings      → detected by font size heuristics
  • Multi-column  → merged left-to-right per page
  • Batch mode    → convert a whole folder at once

Usage
-----
  python pdf2md.py input.pdf                    # outputs input.md
  python pdf2md.py input.pdf -o output.md       # custom output path
  python pdf2md.py ./folder -o ./out_folder     # batch convert folder
  python pdf2md.py input.pdf --ocr              # force OCR mode
  python pdf2md.py input.pdf --no-tables        # skip table detection
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

# ── Optional heavy imports (graceful degradation) ────────────────────────────
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from pdf2image import convert_from_path
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


# ═══════════════════════════════════════════════════════════════════════════
# Core converter
# ═══════════════════════════════════════════════════════════════════════════

class PDF2MD:
    """Converts a single PDF file to Markdown."""

    # Font-size thresholds for heading detection (points)
    H1_SIZE = 20
    H2_SIZE = 16
    H3_SIZE = 13

    def __init__(
        self,
        pdf_path: str | Path,
        force_ocr: bool = False,
        extract_tables: bool = True,
        min_text_length: int = 50,   # chars per page below which we try OCR
    ):
        self.pdf_path = Path(pdf_path)
        self.force_ocr = force_ocr
        self.extract_tables = extract_tables
        self.min_text_length = min_text_length

        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

    # ── Public API ──────────────────────────────────────────────────────────

    def convert(self) -> str:
        """Return the full Markdown string for the PDF."""
        if not HAS_PDFPLUMBER:
            raise RuntimeError(
                "pdfplumber is required. Run: pip install pdfplumber"
            )

        if self.force_ocr:
            return self._convert_ocr()

        return self._convert_digital()

    def save(self, output_path: str | Path | None = None) -> Path:
        """Convert and write to a .md file. Returns the output path."""
        md = self.convert()

        if output_path is None:
            output_path = self.pdf_path.with_suffix(".md")
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(md, encoding="utf-8")
        return output_path

    # ── Digital PDF path ────────────────────────────────────────────────────

    def _convert_digital(self) -> str:
        sections: list[str] = []

        with pdfplumber.open(self.pdf_path) as pdf:
            # Extract metadata header
            meta = self._extract_metadata(pdf)
            if meta:
                sections.append(meta)

            for page_num, page in enumerate(pdf.pages, start=1):
                page_md = self._process_page(page, page_num)
                if page_md.strip():
                    sections.append(page_md)

        return "\n\n".join(sections).strip() + "\n"

    def _process_page(self, page, page_num: int) -> str:
        """Extract text and tables from one page, return as Markdown."""
        parts: list[str] = []

        # Find table bounding boxes so we can skip those regions in text extraction
        tables_md: list[tuple[float, str]] = []   # (top_y, markdown)
        table_bboxes: list[tuple] = []

        if self.extract_tables:
            for table in page.find_tables():
                data = table.extract()
                if data:
                    bbox = table.bbox   # (x0, top, x1, bottom)
                    table_bboxes.append(bbox)
                    tables_md.append((bbox[1], self._table_to_md(data)))

        # Extract text OUTSIDE table bounding boxes
        words = page.extract_words(keep_blank_chars=False, use_text_flow=True)
        text_md = self._words_to_md(words, table_bboxes, page)

        # Detect if page is image-only (scanned) and fall back to OCR
        if len(text_md.strip()) < self.min_text_length and HAS_OCR:
            text_md = self._ocr_page(page)

        # Interleave text and tables in vertical order
        combined: list[tuple[float, str]] = []
        if text_md.strip():
            combined.append((0.0, text_md))
        combined.extend(tables_md)
        combined.sort(key=lambda x: x[0])

        for _, content in combined:
            if content.strip():
                parts.append(content)

        return "\n\n".join(parts)

    def _words_to_md(self, words: list[dict], table_bboxes: list[tuple], page) -> str:
        """Convert extracted words to Markdown, applying heading heuristics."""
        if not words:
            return ""

        # Filter out words inside table regions
        def in_table(w: dict) -> bool:
            for (x0, top, x1, bottom) in table_bboxes:
                if w["x0"] >= x0 and w["x1"] <= x1 and w["top"] >= top and w["bottom"] <= bottom:
                    return True
            return False

        words = [w for w in words if not in_table(w)]
        if not words:
            return ""

        # Group words into lines by vertical position (y tolerance = 3pt)
        lines: list[list[dict]] = []
        current_line: list[dict] = []
        prev_top = None

        for word in words:
            if prev_top is None or abs(word["top"] - prev_top) < 5:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(current_line)
                current_line = [word]
            prev_top = word["top"]
        if current_line:
            lines.append(current_line)

        md_lines: list[str] = []
        prev_bottom = None

        for line in lines:
            text = " ".join(w["text"] for w in line).strip()
            if not text:
                continue

            # Detect paragraph break (large vertical gap)
            top = line[0]["top"]
            if prev_bottom is not None and (top - prev_bottom) > 15:
                md_lines.append("")   # blank line = paragraph break

            # Heading detection via font size
            avg_size = self._avg_font_size(line)
            prefix = self._heading_prefix(avg_size, text)

            if prefix:
                md_lines.append(f"\n{prefix} {text}")
            else:
                md_lines.append(text)

            prev_bottom = line[-1]["bottom"] if line else top

        # Join lines; consecutive non-blank lines become one paragraph
        return self._join_lines(md_lines)

    def _avg_font_size(self, words: list[dict]) -> float:
        sizes = [w.get("size", 0) for w in words if w.get("size")]
        return sum(sizes) / len(sizes) if sizes else 0.0

    def _heading_prefix(self, size: float, text: str) -> str:
        """Return markdown heading prefix based on font size, or '' for body text."""
        # Skip single-word or very long lines from heading detection
        word_count = len(text.split())
        if word_count > 8 or word_count == 0:
            return ""
        if size >= self.H1_SIZE:
            return "#"
        if size >= self.H2_SIZE:
            return "##"
        if size >= self.H3_SIZE:
            return "###"
        return ""

    def _join_lines(self, lines: list[str]) -> str:
        """Merge consecutive non-blank lines into paragraphs."""
        paragraphs: list[str] = []
        current: list[str] = []

        for line in lines:
            if line == "":
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
                paragraphs.append("")
            elif line.startswith("#"):
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
                paragraphs.append(line.strip())
            else:
                current.append(line.strip())

        if current:
            paragraphs.append(" ".join(current))

        # Collapse multiple blank lines
        result = "\n\n".join(p for p in paragraphs if p != "")
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result

    # ── Table conversion ────────────────────────────────────────────────────

    def _table_to_md(self, data: list[list]) -> str:
        """Convert a pdfplumber table (list of rows) to a Markdown pipe table."""
        if not data:
            return ""

        # Clean cells
        def clean(cell) -> str:
            if cell is None:
                return ""
            return str(cell).replace("\n", " ").strip()

        rows = [[clean(cell) for cell in row] for row in data]

        # Determine column count
        col_count = max(len(row) for row in rows)
        rows = [row + [""] * (col_count - len(row)) for row in rows]

        # Build markdown table
        header = rows[0]
        separator = ["---"] * col_count
        body = rows[1:]

        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(separator) + " |",
        ]
        for row in body:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    # ── OCR path ────────────────────────────────────────────────────────────

    def _convert_ocr(self) -> str:
        """Full OCR conversion for scanned PDFs."""
        if not HAS_OCR:
            raise RuntimeError(
                "OCR requires pdf2image and pytesseract.\n"
                "Run: pip install pdf2image pytesseract\n"
                "Also install Tesseract: https://github.com/tesseract-ocr/tesseract"
            )

        images = convert_from_path(str(self.pdf_path), dpi=300)
        sections: list[str] = [f"# {self.pdf_path.stem}\n"]

        for i, image in enumerate(images, start=1):
            text = pytesseract.image_to_string(image, config="--psm 3")
            cleaned = self._clean_ocr_text(text)
            if cleaned.strip():
                sections.append(f"<!-- page {i} -->\n\n{cleaned}")

        return "\n\n---\n\n".join(sections).strip() + "\n"

    def _ocr_page(self, page) -> str:
        """OCR a single pdfplumber page object."""
        if not HAS_OCR:
            return ""
        img = page.to_image(resolution=200).original
        text = pytesseract.image_to_string(img, config="--psm 3")
        return self._clean_ocr_text(text)

    def _clean_ocr_text(self, text: str) -> str:
        """Clean common OCR artifacts."""
        # Remove form feeds
        text = text.replace("\f", "\n\n")
        # Collapse 3+ newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Remove trailing whitespace per line
        text = "\n".join(line.rstrip() for line in text.splitlines())
        return text.strip()

    # ── Metadata ────────────────────────────────────────────────────────────

    def _extract_metadata(self, pdf) -> str:
        """Build a YAML-style frontmatter block from PDF metadata."""
        try:
            meta = pdf.metadata or {}
        except Exception:
            return ""

        fields = {
            "title":   meta.get("Title") or self.pdf_path.stem,
            "author":  meta.get("Author"),
            "subject": meta.get("Subject"),
            "pages":   len(pdf.pages),
            "source":  self.pdf_path.name,
        }

        lines = ["---"]
        for key, val in fields.items():
            if val:
                lines.append(f"{key}: {val}")
        lines.append("---")

        return "\n".join(lines) if len(lines) > 2 else ""


# ═══════════════════════════════════════════════════════════════════════════
# Batch conversion
# ═══════════════════════════════════════════════════════════════════════════

def batch_convert(
    input_dir: Path,
    output_dir: Path,
    force_ocr: bool = False,
    extract_tables: bool = True,
) -> list[tuple[Path, Path | Exception]]:
    """Convert all PDFs in input_dir, write .md files to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(input_dir.glob("*.pdf"))

    if not pdfs:
        print(f"No PDF files found in {input_dir}")
        return []

    results: list[tuple[Path, Path | Exception]] = []

    for pdf_path in pdfs:
        out_path = output_dir / pdf_path.with_suffix(".md").name
        try:
            converter = PDF2MD(pdf_path, force_ocr=force_ocr, extract_tables=extract_tables)
            saved = converter.save(out_path)
            print(f"  ✓  {pdf_path.name}  →  {saved.name}")
            results.append((pdf_path, saved))
        except Exception as exc:
            print(f"  ✗  {pdf_path.name}  →  ERROR: {exc}")
            results.append((pdf_path, exc))

    return results


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert PDF files to Markdown.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="PDF file or folder of PDFs")
    parser.add_argument("-o", "--output", help="Output .md file or folder", default=None)
    parser.add_argument("--ocr", action="store_true", help="Force OCR mode (for scanned PDFs)")
    parser.add_argument("--no-tables", action="store_true", help="Disable table extraction")
    args = parser.parse_args()

    input_path = Path(args.input)

    # Batch mode
    if input_path.is_dir():
        out_dir = Path(args.output) if args.output else input_path / "markdown"
        print(f"Batch converting PDFs in: {input_path}")
        results = batch_convert(input_path, out_dir, force_ocr=args.ocr, extract_tables=not args.no_tables)
        success = sum(1 for _, r in results if not isinstance(r, Exception))
        print(f"\nDone: {success}/{len(results)} converted → {out_dir}")
        return

    # Single file
    if not input_path.suffix.lower() == ".pdf":
        print(f"Error: input must be a .pdf file or directory, got: {input_path}")
        sys.exit(1)

    out_path = Path(args.output) if args.output else None

    try:
        converter = PDF2MD(input_path, force_ocr=args.ocr, extract_tables=not args.no_tables)
        saved = converter.save(out_path)
        print(f"✓ Converted: {input_path.name} → {saved}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
