from typing import Literal

from ...core.domain import Relation


class Dependency(Relation):
    operator: Literal["->"] = "->"
