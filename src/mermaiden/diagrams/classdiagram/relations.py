from enum import StrEnum

from pydantic import Field

from ...core.domain import Relation
from .values.text import ClassIdentifier, OptionalClassText


class ClassRelationKind(StrEnum):
    ASSOCIATION = "association"
    INHERITANCE = "inheritance"
    COMPOSITION = "composition"
    AGGREGATION = "aggregation"
    DEPENDENCY = "dependency"
    REALIZATION = "realization"


class ClassRelation(Relation):
    id: str = Field(pattern=ClassIdentifier.pattern, description=ClassIdentifier.description)
    label: str = Field(default="", pattern=OptionalClassText.pattern, description=OptionalClassText.description)
    relation_kind: ClassRelationKind = ClassRelationKind.ASSOCIATION
    source_label: str = Field(default="", pattern=OptionalClassText.pattern, description=OptionalClassText.description)
    target_label: str = Field(default="", pattern=OptionalClassText.pattern, description=OptionalClassText.description)
