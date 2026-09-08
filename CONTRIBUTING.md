# Contributing

Keep contracts frozen, strict, discriminated, and immutable. Required semantics stay explicit;
optional values use `None` and collections use tuples. Consumer-owned extension ports use small
Protocols. Package code performs no file or process I/O, and feature packages expose intentional
`__all__` APIs without importing sibling features.

Generated README regions project root `__all__`, public docstrings, and the executable example. Edit
those sources and run `make docs`; never hand-edit generated regions.

```bash
uv sync --all-groups --frozen
make fast-check
make integration
make ci
```
