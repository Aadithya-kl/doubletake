# Changelog

## 0.2.1 (2026-11-23)

- **GitHub Action**: `uses: Aadithya-kl/doubletake@v0.2.1`, with job summary, SARIF, a `leaks` output and installation of only the system packages your formats need.
- Published on PyPI as **`doubletake-ai`** (the `doubletake` name belongs to an unrelated project). The command and import name stay `doubletake`.
- Release workflow with PyPI trusted publishing.
- `doubletake selftest --format` checks only the formats you use. The Action passes its `formats` through, so a PDF-only run no longer needs LibreOffice.
- Hero image, social preview, issue and PR templates, code of conduct, citation file.

## 0.2.0 (2026-11-23)

- New carriers: **XLSX** (hidden and very-hidden sheets, hidden rows and columns, white text, cell comments),
  **PPTX** (speaker notes, off-slide, white text, 1pt font, hidden shape, covered shape) and
  **EML** (`text/plain` vs `text/html` mismatch, hidden HTML, custom `X-` header). 37 techniques in total.
- New built-in parsers: openpyxl (all cells, visible-only, comments), python-pptx (with and without notes),
  Python `email` (plain-preferred, HTML-preferred, all parts and headers); markitdown now covers XLSX and PPTX.
- `--llm`: optional obedience check against any OpenAI-compatible endpoint, with caching and a request cap.
- `--sarif` for `probe` and `scan` (SARIF 2.1.0, ready for GitHub code scanning).
- `doubletake selftest`: positive controls for every format.
- Human-view safeguards: renders that do not show the cover text are never counted as hidden; OCR-tolerant
  canary matching; canary alphabet without OCR look-alikes.
- `scan` accepts every supported format and multiple files, prints JSON for all of them, and ignores raw
  markup and full header dumps when diffing.
- Documentation: techniques (generated from real results), custom parsers, LLM mode, CI, mitigations.

## 0.1.0

- First version: PDF, DOCX and HTML techniques, `probe`, `scan` and `forge`, custom command and Python parsers.
