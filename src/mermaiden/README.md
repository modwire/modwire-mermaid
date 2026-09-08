# Diagram core prototype

The model has five concepts:

- **Diagram** owns its state and is the Visitor host.
- **Element** is either an entity or a recursively nested container.
- **Relation** binds IDs of existing elements.
- **Constraint** is a side-effect-free Visitor producing structured violations.
- **Annotation** adds data through typed references to elements or relations.

Dependency direction is `flowchart/treeview -> runtime -> core`. Core is independent of
Wireup and Mermaid. Runtime is a service-oriented building environment: frozen
dataclass services receive dependencies through typed fields, while transient
diagram aggregates own isolated state. The process-owned composition root reuses
immutable singleton services. No service has a handwritten constructor.

Every mutation is executed by a Unit of Work. An Observer evaluates constraints
before and after staging the candidate. Blocking violations roll the candidate
back atomically; advisory violations allow deliberately incomplete diagrams to
be built and repaired incrementally.

Flowchart and Tree View are separate aggregates resolved from the composition root. Flowchart's API
uses domain operations such as `add_start`, `add_decision`, `add_flow`, and
`remove_flow`. Callers pass primitive arguments; the aggregate creates its
`FlowNode`, `Flow`, and `Note` values internally. Generic `Diagram` operations
are mapped to the same flowchart vocabulary and the same constraint pipeline,
so they cannot bypass domain rules.

The principal patterns are:

- **Aggregate** for state ownership and behavior boundaries,
- **Composite** for recursive element containment,
- **Visitor** for structural and diagram-specific constraints,
- **Observer** for before/after constraint evaluation,
- **Unit of Work / Memento** for stage, commit, and rollback,
- **Strategy** through the injected change and inspection contracts.

Rendering implementations remain outside core. A renderer consumes the
read-only `DiagramView` contract through `root_elements`, `walk_elements`,
`find_relations`, and `find_annotations`, without access to runtime state or
mutation services. The generic `Renderer` strategy does not prescribe a
technology or output type.

The generic `rendering` adapter package provides strict Jinja-to-text rendering
and canonical LF-only output. It contains no Mermaid syntax and can be reused by
diagram-specific rendering packages.

The accepted initial flowchart surface is documented in
[`diagrams/flowchart/VOCABULARY.md`](diagrams/flowchart/VOCABULARY.md).

Each diagram rendering package emits deterministic Mermaid body text through Jinja
snippets. Each semantic element, relation, and annotation owns its Mermaid
representation in a template; renderer Python code only configures safe syntax
filters and invokes the root template. The composition root exposes one
`MermaidRenderer`, which dispatches every supported diagram and applies the
same default Mermaid `wrap: true` document configuration.
