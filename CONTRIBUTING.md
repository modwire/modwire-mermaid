# Contributing

Keep contracts frozen, strict, discriminated, and immutable. Required semantics stay explicit;
optional values use `None` and collections use tuples. Consumer-owned extension ports use small
Protocols. Package code performs no file or process I/O, and feature packages expose intentional
`__all__` APIs without importing sibling features.

Generated README regions project root `__all__`, public docstrings, and the executable example. Edit
those sources and run `make docs`; never hand-edit generated regions.

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
