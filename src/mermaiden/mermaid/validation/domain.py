from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

MERMAID_VERSION = "11.16.0"


class MermaidRenderDiagnosticCode(StrEnum):
    DIAGRAM_INVALID = "diagram_invalid"
    SOURCE_GENERATION_FAILED = "source_generation_failed"
    RENDERER_UNAVAILABLE = "renderer_unavailable"
    RENDER_TIMEOUT = "render_timeout"
    RENDER_FAILED = "render_failed"
    SVG_MISSING = "svg_missing"
    SVG_EMPTY = "svg_empty"
    SVG_ERROR = "svg_error"


@dataclass(frozen=True, slots=True)
class MermaidRenderDiagnostic:
    code: MermaidRenderDiagnosticCode
    message: str
    details: str = ""


@dataclass(frozen=True, slots=True)
class MermaidRenderReport:
    diagram_id: str
    mermaid_version: str
    svg: str = ""
    diagnostics: tuple[MermaidRenderDiagnostic, ...] = ()

    @property
    def success(self) -> bool:
        return bool(self.svg.strip()) and not self.diagnostics


@dataclass(frozen=True, slots=True)
class MermaidCliResult:
    return_code: int | None
    svgs: Mapping[str, str]
    output: str = ""
    timed_out: bool = False
