# Security policy

## Reporting a vulnerability in DoubleTake

DoubleTake opens untrusted documents with third-party parsers and renderers (pypdf, LibreOffice,
headless Chrome, and others). If you find a way to make DoubleTake itself execute code, read files outside
its working folder, or leak data, please report it privately through
[GitHub Security Advisories](https://github.com/Aadithya-kl/doubletake/security/advisories/new) rather than
in a public issue. You can expect an acknowledgement within a week.

## Running DoubleTake safely

- `scan` processes documents you did not create. Run it in a container or VM with no credentials when you
  scan files from untrusted sources, as you would any document converter.
- Headless Chrome is started with `--no-sandbox` so it works in containers. Do not run DoubleTake as root on
  a machine that holds secrets.
- `--llm` sends parser output to the endpoint you configure. The forged documents contain only synthetic
  data; custom parsers may add more.

## Findings about other software

A parser that returns hidden text is usually doing exactly what a text extractor is designed to do. Report
that to the library as a feature request. For hosted AI products, follow the vendor's disclosure policy and
use only the harmless DoubleTake payload when demonstrating the issue.
