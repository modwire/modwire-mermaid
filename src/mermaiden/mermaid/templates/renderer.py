from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from wireup import injectable

from ...core.domain import DiagramView
from .value_formatter import MermaidValueFormatter


@injectable
@dataclass(frozen=True, slots=True)
class MermaidTemplateRenderer:
    values: MermaidValueFormatter
    environment: Environment = field(init=False)

    def __post_init__(self) -> None:
        environment = Environment(
            loader=FileSystemLoader(Path(__file__).parent.parent),
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
            newline_sequence="\n",
        )
        environment.filters.update(
            {
                "mermaid_id": self.values.identifier,
                "mermaid_entity_quote": self.values.entity_quote,
                "mermaid_number": self.values.number,
                "mermaid_quote": self.values.quote,
                "class_text": self.values.class_text,
                "tree_label": self.values.tree_label,
            }
        )
        object.__setattr__(self, "environment", environment)

    def render(self, diagram: DiagramView) -> str:
        return self.environment.get_template(self.document_template(diagram)).render(
            diagram=diagram,
            template_prefix=self.template_prefix(diagram),
        )

    def require(self, template: str) -> None:
        self.environment.get_template(template)

    def document_template(self, diagram: DiagramView) -> str:
        return f"{self.template_prefix(diagram)}/document.mmd.j2"

    def template_prefix(self, diagram: DiagramView) -> str:
        return f"templates/syntax/{diagram.kind}"
