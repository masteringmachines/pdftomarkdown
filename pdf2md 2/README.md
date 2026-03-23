# pdf2md 📄→📝

Convert any PDF to clean, structured Markdown. Handles digital PDFs, scanned documents (OCR), tables, and headings — in a single Python file with no server required.

## Quick start

```bash
pip install pdfplumber
python pdf2md.py document.pdf
```

Output: `document.md` in the same directory.

## Install

```bash
pip install -r requirements.txt
```

For scanned PDFs (OCR), also install Tesseract:

| Platform | Command |
|---|---|
| macOS | `brew install tesseract` |
| Ubuntu | `sudo apt install tesseract-ocr` |
| Windows | [Download installer](https://github.com/tesseract-ocr/tesseract/wiki) |

## Usage

```bash
# Single file
python pdf2md.py input.pdf

# Custom output path
python pdf2md.py input.pdf -o notes/output.md

# Batch convert a folder
python pdf2md.py ./pdfs -o ./markdown

# Force OCR mode (scanned PDFs)
python pdf2md.py scanned.pdf --ocr

# Skip table extraction
python pdf2md.py input.pdf --no-tables
```

## Python API

```python
from pdf2md import PDF2MD

# Convert and get string
converter = PDF2MD("document.pdf")
markdown = converter.convert()

# Convert and save
converter.save("output.md")

# Batch convert
from pdf2md import batch_convert
from pathlib import Path

batch_convert(Path("./pdfs"), Path("./markdown"))
```

## Features

| Feature | Detail |
|---|---|
| Digital PDFs | Fast text extraction via pdfplumber |
| Scanned PDFs | OCR via pytesseract + pdf2image |
| Tables | Extracted as Markdown pipe tables |
| Headings | Detected by font size heuristics |
| Metadata | YAML frontmatter (title, author, pages) |
| Batch mode | Convert entire folders at once |
| Auto-fallback | Falls back to OCR per-page if text is too short |

## Output example

```markdown
---
title: Annual Report 2024
author: Jane Smith
pages: 12
source: report.pdf
---

# Annual Report 2024

## Executive Summary

Lorem ipsum dolor sit amet...

## Financial Results

| Quarter | Revenue | Profit |
| --- | --- | --- |
| Q1 | $1.2M | $340K |
| Q2 | $1.5M | $410K |
```

## Requirements

- Python 3.8+
- pdfplumber (required)
- pdf2image + pytesseract + Tesseract binary (optional, for OCR)
