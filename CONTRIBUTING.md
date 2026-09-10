# Contributing

Keep contracts frozen, strict, discriminated, and immutable. Required semantics stay explicit; optional values use
`None` and collections use tuples. Public callers use `Application`; concrete diagram features do not import sibling
features, and diagram-level sharing belongs only in `diagrams.shared`. See the
[architecture and ownership map](docs/architecture.md).

Package I/O stays behind explicit application operations: packaged schema and template reads, caller-requested preview
writes, and Mermaid CLI validation. The mutation matrices under `docs/contracts/diagram-mutations` are generated from
the public catalog. Change their source contract or public API, run `make mutation-contract`, and review every generated
JSON and Markdown change.

Set up the locked development environment with the only maintained development dependency group:

```bash
uv sync --locked --group dev
```

Run frozen verification with no manifest or lockfile updates:

```bash
uv lock --check
make ci
```

For an intentional dependency update, edit `pyproject.toml` when the declared constraints need to change, then regenerate
and review the committed lock before verification:

```bash
uv lock
git diff -- pyproject.toml uv.lock
make ci
```
