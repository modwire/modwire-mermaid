# mermaiden

`mermaiden` generates deterministic Mermaid source from typed Python diagram models. It supports the Mermaid syntax families registered by the package and validates each diagram before rendering its text.

The package produces Mermaid text only. Render it with Mermaid in a browser, Markdown viewer, or your own CLI workflow.

## Installation

Python 3.12 or later is required.

```sh
pip install mermaiden
```

The wheel declares and installs its Python dependencies. The `compat` CLI command needs no additional tools.
Full SVG validation through `Application.validate_render()` shells out to the `mmdc` executable and requires a
compatible browser. Development installs the exact Mermaid CLI version from `package-lock.json`; set
`PUPPETEER_EXECUTABLE_PATH` when using a system browser.

## Quick start

```python
from mermaiden import Application

with Application.create() as application:
    diagrams = application.available_diagrams()
    print(diagrams)
```

`Application.available_diagrams()` returns the supported diagram catalog. `Application.diagram_info(diagram_id)` returns the typed diagram API for an individual syntax. CLI workflows are available through `python -m mermaiden.cli`.

## Application API

`Application` is the boundary for API and persistence adapters. It owns its dependency-injection container and scope,
so use it as a context manager or call `close()` explicitly. Create a diagram by Mermaid syntax id, apply a named
domain command, and persist the JSON-safe snapshot returned by the application.

```python
from mermaiden import Application
from mermaiden.application import DiagramCommand

with Application.create() as application:
    diagram = application.create_diagram("sequenceDiagram")
    application.apply(diagram, DiagramCommand("add_participant", {"id": "api", "label": "API"}))

    payload = application.snapshot(diagram).to_dict()
    restored = application.restore(payload)
    source = application.render(restored)
```

Before committing a revision, callers can require Mermaid's complete rendering and layout phase to produce an SVG. The report is non-mutating and identifies the compatible Mermaid version together with structured diagnostics on failure.

```python
report = application.validate_render(restored)
if not report.success:
    raise RuntimeError(report.diagnostics)
svg = report.svg
```

Snapshots have a versioned envelope and may be stored as JSON. Version 6 uses registry-owned discriminators such as
`mermaiden/element/classDiagram/class`; snapshots never contain importable Python module paths. Its closed envelope
schema is published at `src/mermaiden/runtime/snapshot/schema.v6.json`. Earlier and unknown versions are rejected;
there is no implicit migration or compatibility reader. Newly created and incomplete diagrams are marked as drafts:
callers may snapshot and restore them between accepted commands, but `Application.render()` rejects them until their
blocking constraints are resolved. Snapshot parsing and typed hydration reject malformed persisted data, and
restoration verifies snapshots that were recorded as valid. Command argument values use the diagram operation names;
JSON string values are accepted for enum arguments.

The caller can discover the REST contract without maintaining a manifest. `diagram_description()` returns JSON Schema for the diagram's elements, relations, annotations, and commands. `command_payload()` returns the generated Pydantic request model for one command.

```python
description = application.diagram_description("sequenceDiagram")
payload_type = application.command_payload("sequenceDiagram", "add_participant")
payload = payload_type.model_validate({"id": "api", "kind": "control"})
```

Element removal is conservative by default: `remove_element` rejects an element that still has descendants,
relations, or annotations. Passing `cascade: true` removes the complete diagram-defined subtree and every dependent
relation and annotation atomically. In Tree View diagrams, branches define that subtree. Removing the final element
returns the diagram to an empty, persistable draft; drafts have no Mermaid source until they become valid again.

## Updating and moving elements

Mutation arguments are JSON-shaped and validated before the diagram changes. Updates preserve identity, moves preserve the complete subtree, and reorders require the exact current members of one collection. Rejected mutations leave the complete snapshot unchanged.

<!-- mutation-conformance-example:start -->
```python
from mermaiden import Application

with Application.create() as application:
    diagram = application.create_diagram("block")
    application.execute(diagram, "add_group", {"id": "source_example", "label": "Source Example"})
    application.execute(diagram, "add_group", {"id": "target_example", "label": "Target Example"})
    for id, label in (
        ("first_example", "First Example"),
        ("second_example", "Second Example"),
        ("third_example", "Third Example"),
    ):
        application.execute(
            diagram,
            "add_block",
            {"id": id, "label": label, "parent_id": "source_example"},
        )

    application.execute(
        diagram,
        "update_element",
        {"id": "first_example", "kind": "block_node", "changes": {"label": "Updated First Example"}},
    )
    application.execute(
        diagram,
        "move_element",
        {"id": "first_example", "kind": "block_node", "parent_id": "target_example", "position": 0},
    )
    application.execute(
        diagram,
        "reorder_elements",
        {"parent_id": "source_example", "element_ids": ["third_example", "second_example"]},
    )

    for operation, arguments in (
        (
            "update_element",
            {"id": "first_example", "kind": "block_node", "changes": {"id": "renamed_example"}},
        ),
        (
            "move_element",
            {"id": "second_example", "kind": "block_node", "parent_id": "third_example"},
        ),
        (
            "reorder_elements",
            {"parent_id": "source_example", "element_ids": ["second_example"]},
        ),
    ):
        before = application.snapshot(diagram).to_dict()
        try:
            application.execute(diagram, operation, arguments)
        except RuntimeError:
            pass
        else:
            raise AssertionError(f"{operation} unexpectedly succeeded")
        assert application.snapshot(diagram).to_dict() == before

    snapshot = application.snapshot(diagram).to_dict()
    restored = application.restore(snapshot)
    assert application.snapshot(restored).to_dict() == snapshot
    assert application.render(restored) == application.render(diagram)
    report = application.validate_render(restored)
    assert report.success and report.svg
```
<!-- mutation-conformance-example:end -->

## Development

Create the development environment from the committed lock before running repository commands:

```sh
uv sync --locked --group dev
```

The fast tier performs no npm, browser, network, or external Mermaid work:

```sh
make fast-check
```

Full SVG compatibility is an explicit integration tier. It installs the lock-pinned Mermaid CLI once and requires a
compatible browser:

```sh
make integration
```

The complete host-mode CI target runs quality, pytest, Mermaid compatibility, and package verification concurrently:

```sh
make ci
```

GitHub Actions runs quality, pytest, Mermaid compatibility, and package verification concurrently; the `ci` job is their
stable aggregate result for branch protection.

## Release

Releases are versioned by annotated `vX.Y.Z` tags. `make ci` first runs `uv lock --check` and
`uv sync --locked --group dev`, so release verification uses the same committed development lock. After it passes,
create and push the tag, then publish the GitHub release:

```sh
git tag -a v2.0.0 -m "v2.0.0"
git push origin v2.0.0
gh release create v2.0.0 --verify-tag --generate-notes --title v2.0.0
```
