import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassName:
    owner: type[object]

    @property
    def snake_case(self) -> str:
        value = self.owner.__name__
        boundary = re.sub("([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", boundary).lower()
