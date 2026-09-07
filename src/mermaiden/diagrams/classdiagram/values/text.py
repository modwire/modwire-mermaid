from typing import Annotated

from pydantic import Field

ClassText = Annotated[
    str, Field(pattern=r"^[^\s\x00-\x1f\x7f-\x9f](?:[^\x00-\x1f\x7f-\x9f]*[^\s\x00-\x1f\x7f-\x9f])?$")
]
OptionalClassText = Annotated[
    str, Field(pattern=r"^(?:[^\s\x00-\x1f\x7f-\x9f](?:[^\x00-\x1f\x7f-\x9f]*[^\s\x00-\x1f\x7f-\x9f])?)?$")
]
ClassIdentifier = ClassText
MemberName = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
TypeName = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")]
