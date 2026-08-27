import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.utils_chunking import chunk_text
from app.rag_service import format_latex_math
from app.main import get_file_extension


def test_get_file_extension():
    """Verify file extension helper correctly extracts extensions."""
    assert get_file_extension("document.pdf") == ".pdf"
    assert get_file_extension("report.DOCX") == ".docx"
    assert get_file_extension("notes.txt") == ".txt"
    assert get_file_extension("no_extension") == ""


def test_chunk_text_basic():
    """Verify text chunker splits text properly without losing words."""
    sample_text = "SmartDocs AI is an intelligent RAG platform. " * 30
    chunks = chunk_text(sample_text)
    
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)
    assert all(len(c.strip()) > 0 for c in chunks)


def test_latex_math_formatting():
    r"""Verify LaTeX math conversion from raw \( ... \) and \[ ... \] to $ ... $ and $$ ... $$."""
    raw_text = r"The derivative is \(\frac{dy}{dx} = 2x\) and the integral is \[\int x dx = \frac{x^2}{2}\]"
    formatted = format_latex_math(raw_text)
    
    assert r"$\frac{dy}{dx} = 2x$" in formatted
    assert r"$$\int x dx = \frac{x^2}{2}$$" in formatted
    assert r"\(" not in formatted
    assert r"\[" not in formatted