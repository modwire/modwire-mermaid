# Diagram mutation contract

This documentation is generated from public `Application` discovery and `contract.json` semantics.
Run `make mutation-contract` after changing the public catalog or contract semantics.
The [character-policy matrices](characters/README.md) record every advertised command string field.

Contract version: `1`.

## Classifications

| Classification | Meaning |
| --- | --- |
| `updateable` | Public semantic field; partial update preserves object identity. |
| `move_or_reorder_only` | Containment and order are owned by move/reorder commands. |
| `immutable` | Stable object identity or concrete kind. |

## Semantics

- **Stable identity.** Object IDs and concrete kinds are immutable; the required kind discriminator must match the selected object and every update and move preserves both.
- **Partial update.** Only fields in changes are replaced; omitted fields retain their current values.
- **Null.** Explicit null is accepted only when the selected public field schema is nullable.
- **Strict payloads.** Unknown payload and change fields are rejected before dispatch; changes contains at least one field.
- **Move.** Moving changes only direct containment and position, preserves the complete subtree, rejects cycles and incompatible parents, uses an empty parent_id for root, accepts positions 0..N after removing the target, and appends when position is omitted.
- **Reorder.** Reordering requires an exact, duplicate-free permutation of the selected root or container's current direct member IDs; an empty parent_id selects root.
- **Retarget.** Relation members and annotation targets are ordered, preserve the owning object ID, and run existing reference, cardinality, kind, uniqueness, and diagram constraints.
- **No-op.** An unchanged patch, current placement, or current exact order is accepted without changing rendered or persisted state.
- **Atomic rejection.** Argument, operation, constraint, and unexpected failures restore the byte-for-byte snapshot that existed before the command.
- **Invalid pre-state.** Update, move, and reorder commit only when the resulting state can commit, even when the pre-state was already invalid.
- **Discovery.** Each supported operation has one name and a strict JSON-shaped schema discoverable through diagram_description and command_payload.

## Commands

| Operation | Applies to | Required payload | Strictness |
| --- | --- | --- | --- |
| `update_element` | elements | `id`, `kind`, `changes` | unknown fields rejected |
| `update_relation` | relations | `id`, `kind`, `changes` | unknown fields rejected |
| `update_annotation` | annotations | `id`, `kind`, `changes` | unknown fields rejected |
| `move_element` | elements | `id`, `kind`, `parent_id` | unknown fields rejected |
| `reorder_elements` | root and container direct element collections | `parent_id`, `element_ids` | unknown fields rejected |

Dynamic schema sources:

- `object.id_schema`: The selected object's public id property schema.
- `object.kind_const`: A string const containing the selected catalogued object kind.
- `object.updateable_field_schemas`: The selected object's public property schemas whose matrix classification is updateable.

## Applicability matrix

| Diagram | Elements | Relations | Annotations |
| --- | ---: | ---: | ---: |
| [`C4Context`](diagrams/C4Context.md) | 5 | 1 | 0 |
| [`architecture-beta`](diagrams/architecture-beta.md) | 3 | 2 | 1 |
| [`block`](diagrams/block.md) | 3 | 0 | 0 |
| [`classDiagram`](diagrams/classDiagram.md) | 2 | 1 | 1 |
| [`cynefin-beta`](diagrams/cynefin-beta.md) | 1 | 1 | 0 |
| [`erDiagram`](diagrams/erDiagram.md) | 2 | 1 | 0 |
| [`eventmodeling`](diagrams/eventmodeling.md) | 5 | 1 | 0 |
| [`flowchart`](diagrams/flowchart.md) | 11 | 2 | 1 |
| [`gantt`](diagrams/gantt.md) | 4 | 0 | 0 |
| [`gitGraph`](diagrams/gitGraph.md) | 3 | 1 | 0 |
| [`ishikawa-beta`](diagrams/ishikawa-beta.md) | 3 | 1 | 0 |
| [`journey`](diagrams/journey.md) | 2 | 0 | 0 |
| [`kanban`](diagrams/kanban.md) | 2 | 0 | 0 |
| [`mindmap`](diagrams/mindmap.md) | 7 | 0 | 0 |
| [`packet`](diagrams/packet.md) | 1 | 0 | 0 |
| [`pie`](diagrams/pie.md) | 1 | 0 | 0 |
| [`radar-beta`](diagrams/radar-beta.md) | 2 | 0 | 0 |
| [`railroad-ebnf-beta`](diagrams/railroad-ebnf-beta.md) | 9 | 0 | 0 |
| [`requirementDiagram`](diagrams/requirementDiagram.md) | 2 | 1 | 0 |
| [`sankey`](diagrams/sankey.md) | 1 | 1 | 0 |
| [`sequenceDiagram`](diagrams/sequenceDiagram.md) | 2 | 4 | 1 |
| [`stateDiagram-v2`](diagrams/stateDiagram-v2.md) | 8 | 1 | 1 |
| [`swimlane-beta`](diagrams/swimlane-beta.md) | 7 | 2 | 0 |
| [`timeline`](diagrams/timeline.md) | 3 | 0 | 0 |
| [`treeView-beta`](diagrams/treeView-beta.md) | 1 | 1 | 1 |
| [`venn-beta`](diagrams/venn-beta.md) | 3 | 0 | 0 |
| [`wardley-beta`](diagrams/wardley-beta.md) | 3 | 1 | 0 |
