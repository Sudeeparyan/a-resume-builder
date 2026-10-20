"""Hidden characters and tool metadata never leave on a resume (backend/ai_marks.py, from the Template)."""

from pypdf import PdfReader, PdfWriter

from career import tex_escape

from backend.ai_marks import clean_pdf, clean_text, find_marks, pdf_leftovers


def test_hidden_characters_and_look_alike_letters_never_reach_the_latex():
    pasted = "Built​ data pipelines in Pythоn with SQL﻿"  # zero-width, Cyrillic o, nbsp, BOM
    assert find_marks(pasted)
    cleaned = clean_text(pasted)
    assert cleaned == "Built data pipelines in Python with SQL" and not find_marks(cleaned)
    assert tex_escape(pasted) == "Built data pipelines in Python with SQL"


def test_a_word_in_another_alphabet_is_left_alone():
    assert clean_text("Москва and Python") == "Москва and Python"


def test_a_compiled_pdf_keeps_only_its_title_and_author(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": "Annie Prasanna Manoharan Resume", "/Author": "Annie Prasanna Manoharan",
                         "/Producer": "xdvipdfmx", "/Creator": "LaTeX with hyperref", "/CreationDate": "D:20261009"})
    path = tmp_path / "resume.pdf"
    with open(path, "wb") as handle:
        writer.write(handle)
    assert set(pdf_leftovers(path)) == {"/Producer", "/Creator", "/CreationDate"}
    assert set(clean_pdf(path)) == {"/Producer", "/Creator", "/CreationDate"}
    metadata = PdfReader(str(path)).metadata
    assert dict(metadata) == {"/Title": "Annie Prasanna Manoharan Resume", "/Author": "Annie Prasanna Manoharan"}
    assert pdf_leftovers(path) == [] and clean_pdf(path) == []
