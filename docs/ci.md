# CI and production use

## Gate pull requests on your ingestion code

`probe --fail-on-leak` exits 1 if any parser leaks a confirmed split-view payload. Point it at the loader
your product actually uses and only the formats you accept:

```yaml
name: doubletake
on:
  pull_request:
    paths: ["src/ingest/**"]
jobs:
  split-view:
    runs-on: ubuntu-latest
    permissions: { security-events: write, contents: read }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: System tools for the human view
        run: sudo apt-get update && sudo apt-get install -y tesseract-ocr poppler-utils libreoffice-writer
      - run: pip install "git+https://github.com/Aadithya-kl/doubletake.git" && pip install -e .
      - run: doubletake selftest
      - run: >
          doubletake probe -q --format pdf --format docx
          --only pypdf
          --parser-py "myapp.ingest:load_text"
          --sarif doubletake.sarif --fail-on-leak
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with: { sarif_file: doubletake.sarif }
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: doubletake-report, path: doubletake-out/ }
```

Tips:

- Run `doubletake selftest` first. If the runner cannot render a format, results for that format are not
  trustworthy and `selftest` fails loudly.
- Restrict `--format` to what you accept. Ubuntu runners ship Chrome; DOCX, XLSX and PPTX need the matching
  LibreOffice packages (`libreoffice-writer`, `-calc`, `-impress`).
- If you have already accepted some leaks, use `--technique` to gate only the ones you have fixed, and
  widen the list as you go.

## SARIF

Both `probe --sarif` and `scan --sarif` write SARIF 2.1.0.

| Source | ruleId | Level |
|---|---|---|
| probe | the technique id, e.g. `pdf.white_text` | error |
| scan | `DT-SCAN-INSTRUCTION`: hidden, instruction-like text | error |
| scan | `DT-SCAN-TAG-SMUGGLING`: Unicode tag characters | error |
| scan | `DT-SCAN-HIDDEN-TEXT`: hidden text that does not look like an instruction | note |

Each probe result names the parser in `properties.parser`, and its message includes the LLM verdict when `--llm` was used.

## Scanning incoming documents

`scan` works on real files with no canary: it diffs each parser's output against OCR of the rendered page.

```bash
doubletake scan uploads/*.pdf --json > scan.json   # exit 2 if anything risky
```

In a service, call it from Python:

```python
from pathlib import Path
from doubletake.parsers import builtin_parsers
from doubletake.scan import run_scan

report = run_scan(Path("upload.pdf"), [p for p in builtin_parsers() if p.name == "pypdf"])
if report.risky:
    quarantine("upload.pdf", reasons=[s.text for s in report.spans if s.instruction_like])
```

Scanning renders and OCRs every page, which takes about 1 to 3 seconds per page. Use it asynchronously or on a sample,
not on the request path. It is a detector, not a sanitiser: see [mitigations.md](mitigations.md) for fixing the pipeline itself.
