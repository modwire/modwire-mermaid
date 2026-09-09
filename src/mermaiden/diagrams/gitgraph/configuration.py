from pydantic import Field

from ...core.characters import Text
from ..domain import MermaidConfigurationModel, MermaidDiagramConfiguration


class GitGraphNodeLabel(MermaidConfigurationModel):
    width: float = 75
    height: float = 100
    x: float = -25
    y: float = 0


class GitGraphDiagramConfiguration(MermaidDiagramConfiguration):
    title_top_margin: int = 25
    diagram_padding: float = 8
    node_label: GitGraphNodeLabel = GitGraphNodeLabel()
    main_branch_name: str = Field(default="main", pattern=Text.pattern, description=Text.description)
    main_branch_order: float = 0
    show_commit_label: bool = True
    show_branches: bool = True
    rotate_commit_label: bool = True
    parallel_commits: bool = False
    arrow_marker_absolute: bool = False
