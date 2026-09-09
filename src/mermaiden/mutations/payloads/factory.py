from collections.abc import Mapping, Sequence
from typing import cast

from pydantic import TypeAdapter
from pydantic_core import CoreSchema, core_schema
from wireup import injectable

from ...core.characters import OptionalIdentifier
from ...core.domain import Annotation, ClassifiedValueModel, Element, Relation
from ...diagrams.catalog.domain import MutationPayloadFactory
from ...domain import CommandPayload, CommandPayloadSchema


@injectable(as_type=MutationPayloadFactory, lifetime="scoped")
class PydanticMutationPayloadFactory(MutationPayloadFactory):
    def element(
        self,
        diagram_name: str,
        object_types: Mapping[str, type[Element]],
    ) -> CommandPayload:
        return self._create(diagram_name, "update_element", object_types)

    def relation(
        self,
        diagram_name: str,
        object_types: Mapping[str, type[Relation]],
    ) -> CommandPayload:
        return self._create(diagram_name, "update_relation", object_types)

    def annotation(
        self,
        diagram_name: str,
        object_types: Mapping[str, type[Annotation]],
    ) -> CommandPayload:
        return self._create(diagram_name, "update_annotation", object_types)

    def move_element(
        self,
        diagram_name: str,
        object_types: Mapping[str, type[Element]],
    ) -> CommandPayload:
        variants = {
            kind: self._move_variant(diagram_name, kind, object_type) for kind, object_type in object_types.items()
        }
        return self._payload("move_element", variants, ("position",))

    def _create(
        self,
        diagram_name: str,
        command_name: str,
        object_types: Mapping[str, type[ClassifiedValueModel]],
    ) -> CommandPayload:
        variants = {
            kind: self._variant(diagram_name, command_name, kind, object_type)
            for kind, object_type in object_types.items()
        }
        return self._payload(command_name, variants, ())

    def _payload(
        self,
        command_name: str,
        variants: Mapping[str, CoreSchema],
        invocation_defaults: Sequence[str],
    ) -> CommandPayload:
        if not variants:
            raise ValueError(f"Command '{command_name}' has no object payloads.")
        schema = core_schema.tagged_union_schema(dict(variants), discriminator="kind")
        return CommandPayloadSchema(schema, invocation_defaults)

    def _variant(
        self,
        diagram_name: str,
        command_name: str,
        kind: str,
        object_type: type[ClassifiedValueModel],
    ) -> CoreSchema:
        change_fields: dict[str, core_schema.TypedDictField] = {}
        for name, field in object_type.model_fields.items():
            if name == "id" or name == "elements":
                continue
            field_schema = TypeAdapter[object](field.rebuild_annotation()).core_schema
            json_schema_extra: object = field.json_schema_extra
            if isinstance(json_schema_extra, dict):
                metadata = dict(field_schema.get("metadata", {}))
                metadata["pydantic_js_extra"] = cast(dict[str, object], json_schema_extra)
                field_schema = cast(CoreSchema, {**field_schema, "metadata": metadata})
            change_fields[name] = core_schema.typed_dict_field(field_schema, required=False)
        changes = core_schema.no_info_after_validator_function(
            self._require_changes,
            core_schema.typed_dict_schema(change_fields, extra_behavior="forbid"),
            ref=f"{diagram_name}_{command_name}_{kind}_changes",
            metadata={"pydantic_js_updates": {"minProperties": 1}},
        )
        fields = {
            "id": core_schema.typed_dict_field(
                TypeAdapter[object](object_type.model_fields["id"].rebuild_annotation()).core_schema,
                required=True,
            ),
            "kind": core_schema.typed_dict_field(core_schema.literal_schema([kind]), required=True),
            "changes": core_schema.typed_dict_field(changes, required=True),
        }
        return core_schema.typed_dict_schema(
            fields,
            extra_behavior="forbid",
            ref=f"{diagram_name}_{command_name}_{kind}_payload",
        )

    def _move_variant(
        self,
        diagram_name: str,
        kind: str,
        object_type: type[Element],
    ) -> CoreSchema:
        fields = {
            "id": core_schema.typed_dict_field(
                TypeAdapter[object](object_type.model_fields["id"].rebuild_annotation()).core_schema,
                required=True,
            ),
            "kind": core_schema.typed_dict_field(core_schema.literal_schema([kind]), required=True),
            "parent_id": core_schema.typed_dict_field(
                TypeAdapter[object](OptionalIdentifier).core_schema,
                required=True,
            ),
            "position": core_schema.typed_dict_field(
                core_schema.with_default_schema(core_schema.int_schema(ge=0, strict=True), default=None),
                required=False,
            ),
        }
        return core_schema.typed_dict_schema(
            fields,
            extra_behavior="forbid",
            ref=f"{diagram_name}_move_element_{kind}_payload",
        )

    def _require_changes(self, value: object) -> object:
        if not isinstance(value, dict) or not value:
            raise ValueError("Changes must contain at least one field.")
        return cast(dict[object, object], value)
