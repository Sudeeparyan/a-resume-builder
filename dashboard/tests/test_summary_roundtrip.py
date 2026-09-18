"""
SUMMARY.md is written by the dashboard and read back by the dashboard.

That round trip used to corrupt itself. A job title containing a pipe -- German
ads write "(m|w|d)", plenty of boards write "Engineer | London" -- was
interpolated raw into a markdown table, which split the row into extra columns.
WorkspaceSource then read *every* "|" line in the file back as a job, so the
header row of the exclusions table became a company called "Role" applying for a
job called "Why". Those got scored, excluded, written back, and produced the
same garbage again on the next scan.

Two fixes, one test file: escape the cell, and read only the shortlist section.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.sources.feeds import _shortlist_block  # noqa: E402
from backend.services.workspace_sync import md_cell  # noqa: E402

PIPED_TITLES = [
    "Senior QA Engineer | London",
    "(Senior) Backend Engineer - idealo Intelligence (m|w|d)",
    "Global Product & Brand Manager (m/w/d) | Hair Professional",
]


# -- escaping --------------------------------------------------------------

def test_pipe_in_a_title_is_escaped():
    for title in PIPED_TITLES:
        assert "|" in title, "test data must actually contain a pipe"
        assert "\\|" in md_cell(title)


def test_escaped_cell_keeps_the_row_intact():
    """A row built from piped values still has exactly its declared columns."""
    row = f"| 1 | {md_cell('Acme | Corp')} | {md_cell('Engineer (m|w|d)')} | C |"
    # split on pipes that are not escaped
    import re
    cells = [c for c in re.split(r"(?<!\\)\|", row.strip().strip("|")) if c.strip()]
    assert len(cells) == 4, cells


def test_md_cell_leaves_ordinary_text_alone():
    assert md_cell("Data Engineer") == "Data Engineer"
    assert md_cell("") == ""


def test_md_cell_still_collapses_whitespace_and_truncates():
    assert md_cell("a\t\n  b") == "a b"
    assert len(md_cell("x" * 500, 40)) == 40


# -- scoping ---------------------------------------------------------------

SUMMARY = """# Your job search

## Your resumes

| # | Company | Role | Folder |
|---|---------|------|--------|
| 1 | Databricks | AI Engineer | `f` |

## Companies found, no resume yet

| # | Company | Role | Tier | Sponsor evidence | Location | Score | Link |
|---|---------|------|------|------------------|----------|-------|------|
| 1 | Real Company | Data Engineer | C | none | Remote | 50 | [Apply](https://x.test/1) |

## Excluded

| Company | Role | Why | Triggering sentence |
|---------|------|-----|---------------------|
| Foo Inc | Bar | Above her level | 'senior' in the title |

## How the sponsorship rule works

| What the posting says | What happens |
|---|---|
| Explicitly will not sponsor | Excluded |
"""


def test_shortlist_block_is_only_the_shortlist():
    block = _shortlist_block(SUMMARY)
    assert "Real Company" in block
    assert "Databricks" not in block          # the resumes table
    assert "Foo Inc" not in block             # the exclusions table
    assert "Triggering sentence" not in block  # its header row
    assert "Explicitly will not sponsor" not in block


def test_the_phantom_job_is_gone():
    """
    "| Company | Role | Why | Triggering sentence |" must never yield a job
    whose company is "Role" -- that was the exact corruption.
    """
    rows = []
    for line in _shortlist_block(SUMMARY).splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or set(cells[0]) <= set("-: "):
            continue
        if cells[1].lower() in ("company", "#"):
            continue
        rows.append(cells[1])
    assert rows == ["Real Company"], rows


def test_missing_heading_yields_nothing_not_everything():
    """A SUMMARY without the shortlist heading must import zero jobs, not all."""
    assert _shortlist_block("# nothing here\n\n| a | b | c | d |\n") == ""
