from pydantic import Field

from ..domain import MermaidDiagramConfiguration


class PacketConfiguration(MermaidDiagramConfiguration):
    row_height: float = Field(default=32, ge=1)
    bit_width: float = Field(default=32, ge=1)
    bits_per_row: float = Field(default=32, ge=1)
    show_bits: bool = True
    padding_x: float = Field(default=5, ge=0)
    padding_y: float = Field(default=5, ge=0)
