"""
tests/test_pdf2md.py — Unit tests for pdf2md (no PDF files needed).
Run with: python -m pytest tests/ -v
"""

import pytest
from pdf2md import PDF2MD


# ── Heading detection ────────────────────────────────────────────────────────

class TestHeadingDetection:
    def setup_method(self):
        # Instantiate without a real file by patching __init__ check
        import unittest.mock as mock
        with mock.patch("pathlib.Path.exists", return_value=True):
            self.c = PDF2MD("fake.pdf")

    def test_h1(self):
        assert self.c._heading_prefix(22, "Big Title") == "#"

    def test_h2(self):
        assert self.c._heading_prefix(17, "Section Title") == "##"

    def test_h3(self):
        assert self.c._heading_prefix(14, "Subsection") == "###"

    def test_body(self):
        assert self.c._heading_prefix(11, "Normal paragraph text here") == ""

    def test_long_line_not_heading(self):
        long = "This is a very long sentence that should never be a heading"
        assert self.c._heading_prefix(22, long) == ""


# ── Table conversion ─────────────────────────────────────────────────────────

class TestTableConversion:
    def setup_method(self):
        import unittest.mock as mock
        with mock.patch("pathlib.Path.exists", return_value=True):
            self.c = PDF2MD("fake.pdf")

    def test_basic_table(self):
        data = [["Name", "Age"], ["Alice", "30"], ["Bob", "25"]]
        md = self.c._table_to_md(data)
        assert "| Name | Age |" in md
        assert "| --- | --- |" in md
        assert "| Alice | 30 |" in md

    def test_none_cells(self):
        data = [["A", None, "C"], ["1", "2", None]]
        md = self.c._table_to_md(data)
        assert "| A |  | C |" in md

    def test_empty_table(self):
        assert self.c._table_to_md([]) == ""

    def test_uneven_rows(self):
        data = [["H1", "H2", "H3"], ["only one"]]
        md = self.c._table_to_md(data)
        lines = md.strip().split("\n")
        # All rows should have same number of pipes
        pipe_counts = [line.count("|") for line in lines]
        assert len(set(pipe_counts)) == 1


# ── OCR text cleaning ────────────────────────────────────────────────────────

class TestOCRCleaning:
    def setup_method(self):
        import unittest.mock as mock
        with mock.patch("pathlib.Path.exists", return_value=True):
            self.c = PDF2MD("fake.pdf")

    def test_removes_form_feed(self):
        result = self.c._clean_ocr_text("page one\fpage two")
        assert "\f" not in result
        assert "page one" in result

    def test_collapses_blank_lines(self):
        result = self.c._clean_ocr_text("line1\n\n\n\n\nline2")
        assert "\n\n\n" not in result

    def test_strips_trailing_whitespace(self):
        result = self.c._clean_ocr_text("hello   \nworld   ")
        for line in result.splitlines():
            assert line == line.rstrip()


# ── Line joining ─────────────────────────────────────────────────────────────

class TestLineJoining:
    def setup_method(self):
        import unittest.mock as mock
        with mock.patch("pathlib.Path.exists", return_value=True):
            self.c = PDF2MD("fake.pdf")

    def test_joins_paragraph(self):
        lines = ["Hello", "world", "today"]
        result = self.c._join_lines(lines)
        assert result == "Hello world today"

    def test_splits_on_blank(self):
        lines = ["Para one", "", "Para two"]
        result = self.c._join_lines(lines)
        assert "Para one" in result
        assert "Para two" in result
        assert "\n\n" in result

    def test_heading_preserved(self):
        lines = ["# Big Title", "body text"]
        result = self.c._join_lines(lines)
        assert "# Big Title" in result
        assert "body text" in result
