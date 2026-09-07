from enum import StrEnum

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
    id: ClassIdentifier
    label: OptionalClassText = ""
    relation_kind: ClassRelationKind = ClassRelationKind.ASSOCIATION
    source_label: OptionalClassText = ""
    target_label: OptionalClassText = ""
