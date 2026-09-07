from pydantic import StrictBool

from ..domain import MermaidDiagramConfiguration


class ClassDiagramConfiguration(MermaidDiagramConfiguration):
    wrap: StrictBool = True
