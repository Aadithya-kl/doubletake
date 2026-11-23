from __future__ import annotations

import sys
from pathlib import Path

import click

from . import __version__
from .forge import FORMATS, by_id, registry
from .parsers import builtin_parsers, command_parser, python_parser, select

_FMT = click.Choice(list(FORMATS))


def _parsers(only, cmds, pys, fmts):
    ps = select(builtin_parsers(), list(only) or None)
    f = set(fmts) if fmts else None
    ps += [command_parser(c, f) for c in cmds]
    ps += [python_parser(p, f) for p in pys]
    if not ps:
        raise click.UsageError("no parsers selected; see `doubletake parsers`")
    return ps


def parser_options(f):
    opts = [
        click.option("--only", multiple=True, metavar="NAME",
                     help="Only run these built-in parsers (repeatable; see `doubletake parsers`)."),
        click.option("--parser", "cmds", multiple=True, metavar="NAME=CMD",
                     help="Your own parser: a shell command that prints text. {file} is replaced by the path."),
        click.option("--parser-py", "pys", multiple=True, metavar="MODULE:FUNC",
                     help="Your own parser: a Python function f(path: str) -> str."),
        click.option("--parser-format", "pfmts", multiple=True, type=_FMT,
                     help="Formats your custom parsers accept (default: all)."),
    ]
    for o in reversed(opts):
        f = o(f)
    return f


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="doubletake")
def main():
    """DoubleTake: find where your document pipeline shows the LLM something the human never saw."""


@main.command()
@parser_options
@click.option("-o", "--out", "outdir", default="doubletake-out", type=click.Path(path_type=Path), show_default=True,
              help="Folder for forged documents and reports.")
@click.option("--format", "fmts", multiple=True, type=_FMT, help="Limit to formats (repeatable).")
@click.option("--technique", "techs", multiple=True, metavar="ID", help="Limit to technique ids (repeatable).")
@click.option("--canary", default=None, help="Use a fixed canary token instead of a random one.")
@click.option("--sarif", "sarif_path", type=click.Path(path_type=Path), help="Also write SARIF 2.1.0 to this path.")
@click.option("--llm", "llm_model", metavar="MODEL",
              help="Also ask this model (OpenAI-compatible API) whether each leak changes its answer.")
@click.option("--llm-base-url", default=None, metavar="URL",
              help="API base URL (default $DOUBLETAKE_LLM_BASE_URL or https://api.openai.com/v1).")
@click.option("--llm-max-calls", default=100, show_default=True, help="Upper bound on LLM requests.")
@click.option("--fail-on-leak", is_flag=True, help="Exit 1 if any parser leaks a hidden payload (for CI).")
@click.option("-q", "--quiet", is_flag=True, help="No progress output.")
def probe(only, cmds, pys, pfmts, outdir, fmts, techs, canary, sarif_path, llm_model, llm_base_url, llm_max_calls,
          fail_on_leak, quiet):
    """Forge split-view documents and test which parsers leak the hidden layer."""
    from .probe import run_probe
    from .report import probe_markdown, probe_terminal, to_json

    known = by_id()
    bad = [t for t in techs if t not in known]
    if bad:
        raise click.UsageError(f"unknown technique(s): {', '.join(bad)}; see `doubletake techniques`")
    llm = None
    if llm_model:
        from .llm import LLMConfig

        llm = LLMConfig.from_env(llm_model, llm_base_url, llm_max_calls)
    rep = run_probe(_parsers(only, cmds, pys, pfmts), outdir, [known[t] for t in techs] or None, set(fmts) or None,
                    canary=canary, llm=llm, progress=(lambda m: None) if quiet else (lambda m: click.echo(f"  {m}", err=True)))
    (outdir / "report.md").write_text(probe_markdown(rep), encoding="utf-8")
    (outdir / "report.json").write_text(to_json(rep), encoding="utf-8")
    if sarif_path:
        from .sarif import dump, probe_sarif

        sarif_path.write_text(dump(probe_sarif(rep)), encoding="utf-8")
    click.echo(probe_terminal(rep))
    click.echo(f"\n  reports: {outdir / 'report.md'}, {outdir / 'report.json'}" + (f", {sarif_path}" if sarif_path else ""))
    if fail_on_leak and rep.leaks():
        sys.exit(1)


@main.command()
@parser_options
@click.argument("files", nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Print JSON instead of Markdown.")
@click.option("--sarif", "sarif_path", type=click.Path(path_type=Path), help="Also write SARIF 2.1.0 to this path.")
@click.option("--min-words", default=4, show_default=True, help="Minimum hidden run length to report.")
def scan(only, cmds, pys, pfmts, files, as_json, sarif_path, min_words):
    """Check real documents for text the model reads but the page does not show.

    Exit code 2 if any document contains hidden instruction-like text or tag smuggling.
    """
    import json

    from .parsers import ext_fmt
    from .report import scan_markdown
    from .scan import run_scan

    ps = _parsers(only, cmds, pys, pfmts)
    reports, risky = [], False
    for f in files:
        if ext_fmt(f) is None:
            click.echo(f"skipping {f}: unsupported format ({', '.join(FORMATS)})", err=True)
            continue
        rep = run_scan(f, ps, min_words=min_words)
        reports.append(rep)
        risky |= rep.risky
        if not as_json:
            click.echo(scan_markdown(rep))
    if as_json:
        click.echo(json.dumps([r.to_dict() for r in reports], indent=2, ensure_ascii=False))
    if sarif_path:
        from .sarif import dump, scan_sarif

        sarif_path.write_text(dump(scan_sarif(reports)), encoding="utf-8")
    sys.exit(2 if risky else 0)


@main.command()
@click.option("-o", "--out", "outdir", default="doubletake-forged", type=click.Path(path_type=Path), show_default=True)
@click.option("--format", "fmts", multiple=True, type=_FMT, help="Limit to formats (repeatable).")
@click.option("--canary", default=None, help="Use a fixed canary token.")
def forge(outdir, fmts, canary):
    """Only generate the split-view documents (e.g. to upload into a hosted product you cannot run locally)."""
    from .canary import new_canary

    canary = canary or new_canary()
    outdir.mkdir(parents=True, exist_ok=True)
    for t in registry():
        if fmts and t.fmt not in fmts:
            continue
        p = t.build(outdir / t.id.replace(".", "_"), canary)
        click.echo(f"{t.id:<26} {p}")
    (outdir / "CANARY.txt").write_text(canary + "\n")
    click.echo(f"\ncanary: {canary}\nUpload the files and ask the system to summarise them. If an answer contains the "
               "canary or calls the invoice 'pre-approved', the system read the hidden layer.")


@main.command()
def selftest():
    """Check that rendering + OCR work here, using documents where the payload is VISIBLE.

    If a visible payload is not detected, the human view is broken and probe results would be false leaks.
    """
    import tempfile

    from .canary import new_canary
    from .forge.controls import CONTROLS
    from .probe import human_view

    canary, ok = new_canary(), True
    with tempfile.TemporaryDirectory() as td:
        for t in CONTROLS:
            seen, err = human_view(t.build(Path(td) / t.id.replace(".", "_"), canary), canary)
            good = seen is True
            ok &= good
            click.echo(f"  {'ok  ' if good else 'FAIL'} {t.fmt:<5} "
                       + ("visible payload detected" if good else (err or "visible payload NOT detected")))
    click.echo("\nselftest passed" if ok else
               "\nselftest FAILED: install the missing renderer (see README) before trusting probe results")
    sys.exit(0 if ok else 1)


@main.command()
@click.option("--format", "fmts", multiple=True, type=_FMT)
def techniques(fmts):
    """List split-view techniques."""
    for t in registry():
        if not fmts or t.fmt in fmts:
            click.echo(f"{t.id:<26} {t.description}")


@main.command()
def parsers():
    """List built-in parsers and whether they are installed."""
    for p in builtin_parsers():
        click.echo(f"{'ok ' if p.available else '-- '} {p.name:<28} {','.join(f for f in FORMATS if f in p.formats)}"
                   + (f"   ({p.note})" if p.note else ""))


if __name__ == "__main__":
    main()
