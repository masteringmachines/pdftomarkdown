# 📄 PDF to Markdown

A Python-powered tool with a web interface that converts any PDF file into clean, readable Markdown. Perfect for turning documents, research papers, reports, and ebooks into a format that's easy to edit, version-control, or feed into AI pipelines.

## ✨ Features

- **One-Click Conversion**: Upload a PDF and instantly get a `.md` file back
- **Web Interface**: Simple browser-based UI — no command-line knowledge required
- **Structure Preservation**: Retains headings, paragraphs, lists, and basic formatting from the original PDF
- **Python Backend**: Fast, reliable extraction using proven Python PDF libraries
- **Downloadable Output**: Download your converted Markdown file directly from the browser

## 🛠️ Tech Stack

- **Python 3.10+** — backend conversion logic
- **HTML/CSS** — frontend web interface
- **Flask / FastAPI** — web server (serving the upload UI and handling conversion)
- **pdfminer / PyMuPDF / pymupdf4llm** — PDF text and structure extraction

## 📁 Project Structure

```
pdftomarkdown/
├── pdf2md 2/
│   ├── app.py              # Web server entry point
│   ├── converter.py        # PDF → Markdown conversion logic
│   ├── templates/
│   │   └── index.html      # Upload UI
│   ├── static/             # CSS and frontend assets
│   └── requirements.txt    # Python dependencies
├── LICENSE
└── README.md
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

```bash
git clone https://github.com/masteringmachines/pdftomarkdown.git
cd pdftomarkdown/pdf2md\ 2
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run the App

```bash
python app.py
```

Then open your browser and go to:

```
http://localhost:5000
```

## 💡 Usage

1. Open the app in your browser
2. Click **Choose File** and select any PDF
3. Click **Convert**
4. Download your generated `.md` file

### Command-Line Usage (if supported)

```bash
python converter.py --input document.pdf --output document.md
```

## 📝 Example

**Input (PDF text):**
```
Introduction
This paper explores the impact of AI on modern software development...
  • Increased productivity
  • Faster iteration cycles
```

**Output (Markdown):**
```markdown
## Introduction

This paper explores the impact of AI on modern software development...

- Increased productivity
- Faster iteration cycles
```

## 🔍 How It Works

1. The PDF is uploaded through the web interface
2. Python extracts text and structural elements (headings, lists, paragraphs) using a PDF parsing library
3. The extracted content is mapped to Markdown syntax
4. The resulting `.md` file is returned to the user for download

## ⚠️ Limitations

- **Scanned PDFs** (image-only): Text extraction requires OCR (not included by default). Consider integrating Tesseract for scanned documents.
- **Complex layouts**: Multi-column layouts, tables, and heavily formatted PDFs may not convert perfectly.
- **Images**: Embedded images in PDFs are not currently extracted.

## 🤝 Contributing

Pull requests are welcome! Ideas for improvement:
- OCR support for scanned PDFs (Tesseract integration)
- Table extraction and Markdown table formatting
- Batch conversion for multiple PDFs
- API endpoint for programmatic use

## 📝 License

MIT
