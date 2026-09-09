from ..domain import MermaidDiagramConfiguration


class ArchitectureDiagramConfiguration(MermaidDiagramConfiguration):
    use_max_width: bool = True
    padding: float = 40
    icon_size: float = 80
    font_size: float = 16
    randomize: bool = False
    node_separation: float = 75
    ideal_edge_length_multiplier: float = 1.5
    edge_elasticity: float = 0.45
    num_iter: float = 2500
    seed: float = 1
