# Contributing to DoubleTake

Thanks for helping. New techniques, parser adapters, renderers and bug reports are all welcome.

## Development setup

```bash
git clone https://github.com/Aadithya-kl/doubletake.git
cd doubletake
pip install -e ".[parsers,dev]"
sudo apt-get install tesseract-ocr poppler-utils libreoffice-writer libreoffice-calc libreoffice-impress
# plus Google Chrome or Chromium

doubletake selftest
pytest -q
```

The full suite forges and renders every technique, so it takes one to two minutes. All tests must pass
before a pull request is merged.

## Project layout

```
src/doubletake/
  canary.py        canary tokens, normalisation, Unicode tag helpers, OCR-tolerant matching
  forge/           one module per format; each exports TECHNIQUES
    controls.py    positive controls (payload VISIBLE) used by selftest and tests
  parsers.py       built-in "model view" adapters + custom command/Python parsers
  humanview.py     render to pixels (poppler / LibreOffice / Chrome) and OCR
  probe.py         forge x parse x human view -> results
  scan.py          diff parser text vs OCR for real documents
  llm.py           optional OpenAI-compatible obedience check
  report.py        Markdown / terminal / JSON
  sarif.py         SARIF 2.1.0
  cli.py           click CLI
scripts/gen_techniques_doc.py   regenerates docs/techniques.md
tests/                           pytest suite (+ mock_llm.py, a fake OpenAI-compatible server)
```

## Adding a technique

1. Add a builder to the right module in `src/doubletake/forge/`. It receives `(out_path_without_suffix, canary)`,
   must write a document that shows `COVER_TEXT` normally, and hides `payload_for(canary)`.
2. Register it in that module's `TECHNIQUES` list with an id of the form `<format>.<name>`.
3. Add a "why parsers miss it" and "mitigation" entry to `WHY` in `scripts/gen_techniques_doc.py`.
4. Run `pytest -q`. `test_every_technique_hides_payload` checks that the payload really is invisible on
   the rendered page, and `test_every_technique_leaks_through_some_parser_except_annotation` checks
   that at least one parser leaks it. If your technique is meant to be caught by every built-in parser,
   update that test with a comment explaining why.
5. Regenerate the sample run and the techniques doc:

   ```bash
   doubletake probe -q -o examples/sample-run --sarif examples/sample-run/report.sarif
   find examples/sample-run -type f ! -name 'report.*' -delete
   python scripts/gen_techniques_doc.py > docs/techniques.md
   ```

A technique is only useful if it hides the payload in a **real renderer**. If `selftest` passes but your
technique shows `VISIBLE`, the renderer displays it, so it is not a split view.

## Adding a built-in parser

Add a function `fn(path: Path) -> str` to `parsers.py` and a `Parser(...)` entry in `builtin_parsers()`
with the formats it accepts and an availability check, so a missing optional dependency shows as `--` in
`doubletake parsers` instead of crashing. Prefer the library's default, most common usage: the point
is to show how people really call it.

## Adding a format

Add a forge module, register it in `forge/__init__.py` (`FORMATS` and `registry()`), teach
`humanview._to_pdf` to render it, add `parsers.ext_fmt` and `ALL_FORMATS` entries, and add a positive
control in `forge/controls.py`.

## Style

- Python 3.10+, type hints, no new runtime dependencies without discussion.
- Keep payloads harmless and canary-tagged.
- Commit messages: imperative mood, short subject line.

## Reporting a parser's behaviour upstream

If DoubleTake shows a parser leaking hidden content, that is usually expected behaviour for a text
extractor rather than a vulnerability. Open an issue or discussion with the library and suggest an
option to respect visibility, rather than filing a security report.
