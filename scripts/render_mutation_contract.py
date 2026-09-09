from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from mermaiden import Application

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = ROOT / "docs" / "contracts" / "diagram-mutations"
CONTRACT_PATH = CONTRACT_ROOT / "contract.json"
DIAGRAMS_PATH = CONTRACT_ROOT / "diagrams"
DOCUMENT_PATH = CONTRACT_ROOT / "README.md"
CHARACTER_POLICIES_PATH = CONTRACT_ROOT / "character-policies.json"
CHARACTER_DIAGRAMS_PATH = CONTRACT_ROOT / "characters"
CHARACTER_DOCUMENT_PATH = CHARACTER_DIAGRAMS_PATH / "README.md"

JsonObject = dict[str, Any]


def load_contract(path: Path = CONTRACT_PATH) -> JsonObject:
    contract = _read_object(path)
    contract["diagrams"] = discover_diagrams()
    return contract


def discover_diagrams() -> JsonObject:
    diagrams: JsonObject = {}
    with Application.create() as application:
        for info in application.available_diagrams():
            description = application.diagram_description(info.id)
            diagrams[info.id] = {
                "root_collection": {
                    "reorder_command": "reorder_elements",
                    "membership": "Exact permutation of current root element IDs.",
                },
                "elements": {
                    kind: _element_contract(
                        schema,
                        description.placements[kind].allowed_parents,
                    )
                    for kind, schema in description.elements.items()
                },
                "relations": {
                    kind: _object_contract(schema, "relations") for kind, schema in description.relations.items()
                },
                "annotations": {
                    kind: _object_contract(schema, "annotations") for kind, schema in description.annotations.items()
                },
            }
    return diagrams


def _element_contract(schema: Mapping[str, object], allowed_parents: tuple[str, ...]) -> JsonObject:
    contract = _object_contract(schema, "elements")
    contract["placement"] = {
        "move_command": "move_element",
        "allowed_parents": list(allowed_parents),
    }
    fields = _object(contract["fields"], "fields")
    if "elements" in fields:
        contract["child_collection"] = {
            "reorder_command": "reorder_elements",
            "membership": "Exact permutation of current direct child IDs.",
        }
    return contract


def _object_contract(schema: Mapping[str, object], category: str) -> JsonObject:
    properties = _object(schema["properties"], "properties")
    fields = {
        name: "immutable" if name == "id" else "move_or_reorder_only" if name == "elements" else "updateable"
        for name in properties
    }
    contract: JsonObject = {
        "update_command": f"update_{category.removesuffix('s')}",
        "fields": fields,
    }
    if category != "elements":
        contract["retargeting"] = {
            "field": "element_ids" if category == "relations" else "targets",
            "ordered": True,
        }
    contract["kind_classification"] = "immutable"
    return contract


def render_artifacts(contract: Mapping[str, Any]) -> dict[Path, str]:
    classifications = _object(contract["classifications"], "classifications")
    diagrams = _object(contract["diagrams"], "diagrams")
    character_contract = discover_character_policies()
    character_diagrams = _object(character_contract["diagrams"], "character policies.diagrams")
    artifacts = {
        DOCUMENT_PATH: render_overview(contract),
        CHARACTER_POLICIES_PATH: json.dumps(
            {
                "generated_from": character_contract["generated_from"],
                "policies": character_contract["policies"],
            },
            indent=2,
        )
        + "\n",
        CHARACTER_DOCUMENT_PATH: render_character_overview(character_diagrams),
    }
    for diagram_id, value in diagrams.items():
        diagram = _object(value, f"diagrams.{diagram_id}")
        artifacts[DIAGRAMS_PATH / f"{diagram_id}.json"] = (
            json.dumps(
                {"diagram_id": diagram_id, **diagram},
                indent=2,
            )
            + "\n"
        )
        artifacts[DIAGRAMS_PATH / f"{diagram_id}.md"] = render_diagram(diagram_id, diagram, classifications)
    for diagram_id, commands in character_diagrams.items():
        artifacts[CHARACTER_DIAGRAMS_PATH / f"{diagram_id}.json"] = (
            json.dumps(
                {
                    "diagram_id": diagram_id,
                    "generated_from": character_contract["generated_from"],
                    "commands": commands,
                },
                indent=2,
            )
            + "\n"
        )
    return artifacts


def render_overview(contract: Mapping[str, Any]) -> str:
    lines = [
        "# Diagram mutation contract",
        "",
        "This documentation is generated from public `Application` discovery and `contract.json` semantics.",
        "Run `make mutation-contract` after changing the public catalog or contract semantics.",
        "The [character-policy matrices](characters/README.md) record every advertised command string field.",
        "",
        f"Contract version: `{contract['contract_version']}`.",
        "",
        "## Classifications",
        "",
        "| Classification | Meaning |",
        "| --- | --- |",
    ]
    for name, description in _object(contract["classifications"], "classifications").items():
        lines.append(f"| `{name}` | {_escape(str(description))} |")
    lines.extend(("", "## Semantics", ""))
    for item in _list(contract["semantics"], "semantics"):
        semantic = _object(item, "semantics[]")
        lines.append(f"- **{semantic['name']}.** {semantic['rule']}")
    lines.extend(
        (
            "",
            "## Commands",
            "",
            "| Operation | Applies to | Required payload | Strictness |",
            "| --- | --- | --- | --- |",
        )
    )
    for operation, item in _object(contract["commands"], "commands").items():
        command = _object(item, f"commands.{operation}")
        payload = _object(command["payload_schema"], f"commands.{operation}.payload_schema")
        required = ", ".join(f"`{name}`" for name in _strings(payload["required"], "required"))
        strictness = "unknown fields rejected" if payload.get("additionalProperties") is False else "open"
        lines.append(f"| `{operation}` | {command['applies_to']} | {required} | {strictness} |")
    lines.extend(("", "Dynamic schema sources:", ""))
    sources = _object(contract["payload_schema_sources"], "payload_schema_sources")
    for source, description in sources.items():
        lines.append(f"- `{source}`: {description}")
    lines.extend(
        (
            "",
            "## Applicability matrix",
            "",
            "| Diagram | Elements | Relations | Annotations |",
            "| --- | ---: | ---: | ---: |",
        )
    )
    for diagram_id, value in _object(contract["diagrams"], "diagrams").items():
        diagram = _object(value, f"diagrams.{diagram_id}")
        lines.append(
            f"| [`{diagram_id}`](diagrams/{diagram_id}.md)"
            f" | {len(_object(diagram['elements'], 'elements'))}"
            f" | {len(_object(diagram['relations'], 'relations'))}"
            f" | {len(_object(diagram['annotations'], 'annotations'))} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def render_character_overview(diagrams: Mapping[str, Any]) -> str:
    lines = [
        "# Diagram character-policy matrices",
        "",
        "Generated from public `Application` discovery. Do not edit directly.",
        "Shared rule definitions are in [`character-policies.json`](../character-policies.json).",
        "",
    ]
    lines.extend(f"- [`{diagram_id}`]({diagram_id}.json)" for diagram_id in diagrams)
    return "\n".join(lines).rstrip() + "\n"


def discover_character_policies() -> JsonObject:
    policies: JsonObject = {}
    patterns: dict[str, str] = {}
    catalog: list[tuple[str, str, Mapping[str, object]]] = []
    with Application.create() as application:
        for info in application.available_diagrams():
            for operation, schema in application.diagram_description(info.id).commands.items():
                catalog.append((info.id, operation, schema))
                pending: list[Mapping[str, object]] = [schema]
                while pending:
                    node = pending.pop()
                    policy = node.get("x-character-policy")
                    pattern = node.get("pattern")
                    if isinstance(policy, str) and isinstance(pattern, str):
                        patterns[pattern] = policy
                        policies[policy] = {"pattern": pattern, "description": node.get("description", "")}
                    for value in node.values():
                        if isinstance(value, Mapping):
                            pending.append(cast(Mapping[str, object], value))
                        elif isinstance(value, list):
                            pending.extend(
                                cast(Mapping[str, object], item) for item in value if isinstance(item, Mapping)
                            )
    diagrams: JsonObject = {}
    for diagram_id, operation, schema in catalog:
        definitions = _object(schema.get("$defs", {}), "$defs")
        rules: dict[str, list[str]] = {}
        pending = [("$", schema, frozenset())]
        while pending:
            path, node, ancestors = pending.pop()
            reference = node.get("$ref")
            if isinstance(reference, str):
                name = reference.removeprefix("#/$defs/")
                if reference.startswith("#/$defs/") and name not in ancestors:
                    pending.append((path, _object(definitions[name], reference), ancestors | {name}))
                continue
            if node.get("type") == "string":
                rule = ""
                pattern = node.get("pattern")
                enum = node.get("enum")
                constant = node.get("const")
                if isinstance(pattern, str):
                    rule = patterns.get(pattern, "")
                    if not rule:
                        description = node.get("description")
                        rule = description if isinstance(description, str) and description else f"pattern {pattern!r}"
                        policies[rule] = {"pattern": pattern}
                elif isinstance(enum, list):
                    title = node.get("title")
                    rule = f"{title} values" if isinstance(title, str) else f"values {enum}"
                    policies[rule] = {"enum": enum}
                elif isinstance(constant, str):
                    rule = f"constant {constant!r}"
                if not rule:
                    raise ValueError(f"{diagram_id}.{operation}.{path} has no named character rule.")
                if rule not in rules.setdefault(path, []):
                    rules[path].append(rule)
            properties = node.get("properties")
            if isinstance(properties, Mapping):
                pending.extend(
                    (f"{path}.{name}", cast(Mapping[str, object], value), ancestors)
                    for name, value in properties.items()
                    if isinstance(name, str) and isinstance(value, Mapping)
                )
            items = node.get("items")
            if isinstance(items, Mapping):
                pending.append((f"{path}[]", cast(Mapping[str, object], items), ancestors))
            for keyword in ("allOf", "anyOf", "oneOf"):
                variants = node.get(keyword)
                if isinstance(variants, list):
                    pending.extend(
                        (path, cast(Mapping[str, object], value), ancestors)
                        for value in variants
                        if isinstance(value, Mapping)
                    )
        commands = cast(JsonObject, diagrams.setdefault(diagram_id, {}))
        commands[operation] = {path: sorted(rules[path]) for path in sorted(rules)}
    return {
        "generated_from": "Application.diagram_description().commands",
        "policies": {name: policies[name] for name in sorted(policies)},
        "diagrams": diagrams,
    }


def render_diagram(
    diagram_id: str,
    diagram: Mapping[str, Any],
    classifications: Mapping[str, Any],
) -> str:
    root = _object(diagram["root_collection"], f"diagrams.{diagram_id}.root_collection")
    lines = [
        f"# `{diagram_id}` mutation matrix",
        "",
        "Generated from public `Application` discovery. Do not edit directly.",
        "",
        f"Root ordering: `{root['reorder_command']}` over the exact direct-member permutation.",
        "",
    ]
    for category, title in (
        ("elements", "Elements"),
        ("relations", "Relations"),
        ("annotations", "Annotations"),
    ):
        objects = _object(diagram[category], f"diagrams.{diagram_id}.{category}")
        lines.extend((f"## {title}", ""))
        if not objects:
            lines.extend(("None.", ""))
            continue
        lines.extend(
            (
                "| Kind | Update command | Placement or retargeting | Fields |",
                "| --- | --- | --- | --- |",
            )
        )
        for kind, object_value in objects.items():
            item = _object(object_value, f"diagrams.{diagram_id}.{category}.{kind}")
            context = _context(category, item)
            fields = _field_policy(
                _object(item["fields"], f"{diagram_id}.{category}.{kind}.fields"),
                classifications,
            )
            lines.append(f"| `{kind}` | `{item['update_command']}` | {_escape(context)} | {_escape(fields)} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _context(category: str, item: Mapping[str, Any]) -> str:
    if category == "elements":
        placement = _object(item["placement"], "placement")
        parents = ", ".join(f"`{name}`" for name in _strings(placement["allowed_parents"], "allowed_parents"))
        child_order = "; direct children use `reorder_elements`" if "child_collection" in item else ""
        return f"parents: {parents}; move: `{placement['move_command']}`{child_order}"
    retargeting = _object(item["retargeting"], "retargeting")
    return f"`{retargeting['field']}` via `{item['update_command']}`; ordered: `{str(retargeting['ordered']).lower()}`"


def _field_policy(fields: Mapping[str, Any], classifications: Mapping[str, Any]) -> str:
    groups: dict[str, list[str]] = {name: [] for name in classifications}
    for field_name, classification_value in fields.items():
        classification = str(classification_value)
        if classification not in groups:
            raise ValueError(f"Unknown classification {classification!r} for field {field_name!r}.")
        groups[classification].append(f"`{field_name}`")
    return "; ".join(f"{classification}: {', '.join(names)}" for classification, names in groups.items() if names)


def _escape(value: str) -> str:
    return value.replace("|", "\\|")


def _read_object(path: Path) -> JsonObject:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Mutation contract at '{path}' must be a JSON object.")
    return cast(JsonObject, value)


def _object(value: object, path: str) -> JsonObject:
    if not isinstance(value, dict):
        raise ValueError(f"'{path}' must be an object.")
    return cast(JsonObject, value)


def _list(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"'{path}' must be an array.")
    return cast(list[object], value)


def _strings(value: object, path: str) -> tuple[str, ...]:
    items = _list(value, path)
    result: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise ValueError(f"'{path}' must contain only strings.")
        result.append(item)
    return tuple(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the public diagram mutation contract.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="replace generated Markdown")
    mode.add_argument("--check", action="store_true", help="fail when generated Markdown has drifted")
    arguments = parser.parse_args()
    artifacts = render_artifacts(load_contract())
    if arguments.write:
        for path, rendered in artifacts.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered, encoding="utf-8")
        expected = set(artifacts)
        for path in (
            *DIAGRAMS_PATH.glob("*.json"),
            *DIAGRAMS_PATH.glob("*.md"),
            *CHARACTER_DIAGRAMS_PATH.glob("*.json"),
            *CHARACTER_DIAGRAMS_PATH.glob("*.md"),
        ):
            if path not in expected:
                path.unlink()
        return
    if arguments.check:
        drifted = [
            path
            for path, rendered in artifacts.items()
            if not path.exists() or path.read_text(encoding="utf-8") != rendered
        ]
        expected = set(artifacts)
        drifted.extend(
            path
            for path in (
                *DIAGRAMS_PATH.glob("*.json"),
                *DIAGRAMS_PATH.glob("*.md"),
                *CHARACTER_DIAGRAMS_PATH.glob("*.json"),
                *CHARACTER_DIAGRAMS_PATH.glob("*.md"),
            )
            if path not in expected
        )
        if drifted:
            names = ", ".join(str(path.relative_to(ROOT)) for path in sorted(drifted))
            raise SystemExit(f"Generated mutation contract is stale ({names}); run `make mutation-contract`.")
        return
    print(artifacts[DOCUMENT_PATH], end="")


if __name__ == "__main__":
    main()
