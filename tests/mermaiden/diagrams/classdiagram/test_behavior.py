import json

import pytest

from mermaiden.application import Application, DiagramCommand, UnknownCommand


class TestClassDiagram:
    def test_restores_a_populated_diagram_with_identical_mermaid(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")

        for command in (
            DiagramCommand("configure", {"wrap": False}),
            DiagramCommand("add_namespace", {"id": "domain", "label": "Domain", "comment": "Types"}),
            DiagramCommand(
                "add_class",
                {
                    "id": "animal",
                    "label": 'Animal "kind"',
                    "parent_id": "domain",
                    "attributes": [{"name": "name", "type": {"name": "String"}, "visibility": "public"}],
                    "methods": [{"name": "sound", "return_type": {"name": "void"}, "visibility": "public"}],
                    "annotations": ["abstract"],
                },
            ),
            DiagramCommand("add_class", {"id": "duck", "label": "Duck", "parent_id": "domain"}),
            DiagramCommand(
                "add_relation",
                {
                    "id": "inherits",
                    "source_id": "duck",
                    "target_id": "animal",
                    "relation_kind": "inheritance",
                    "label": "extends",
                },
            ),
            DiagramCommand("add_note", {"id": "note", "class_id": "animal", "text": 'Base "type"'}),
        ):
            application.apply(diagram, command)

        source = application.render(diagram)
        restored = application.restore(json.loads(json.dumps(application.snapshot(diagram).to_dict())))

        assert 'namespace c_v_domain["Domain"]' in source
        assert "abstract" in source
        assert "--|>" in source
        assert "note for c_v_animal" in source
        assert application.render(restored) == source

    @pytest.mark.parametrize(
        ("relation_kind", "connector"),
        (
            ("association", "--"),
            ("inheritance", "--|>"),
            ("composition", "--*"),
            ("aggregation", "--o"),
            ("dependency", "..>"),
            ("realization", "..|>"),
        ),
    )
    def test_relation_markers_follow_semantic_source_to_target_through_update_and_restore(
        self,
        relation_kind: str,
        connector: str,
    ) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")
        application.execute(diagram, "add_class", {"id": "source", "label": "Source"})
        application.execute(diagram, "add_class", {"id": "target", "label": "Target"})
        application.execute(diagram, "add_class", {"id": "new_target", "label": "New target"})
        application.execute(
            diagram,
            "add_relation",
            {
                "id": "relation",
                "source_id": "source",
                "target_id": "target",
                "relation_kind": relation_kind,
                "label": "uses",
                "source_label": "one",
                "target_label": "many",
            },
        )

        source = application.render(diagram)
        assert f'c_v_source "one" {connector} "many" c_v_target : uses' in source

        restored = application.restore(json.loads(json.dumps(application.snapshot(diagram).to_dict())))
        assert application.render(restored) == source

        application.execute(
            restored,
            "update_relation",
            {
                "id": "relation",
                "kind": "class_relation",
                "changes": {"element_ids": ["source", "new_target"]},
            },
        )
        updated_source = application.render(restored)
        assert f'c_v_source "one" {connector} "many" c_v_new_target : uses' in updated_source

        updated = application.restore(json.loads(json.dumps(application.snapshot(restored).to_dict())))
        assert application.render(updated) == updated_source

    def test_rejects_bad_relations_duplicate_classes_and_unknown_note_targets(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")
        application.apply(diagram, DiagramCommand("add_class", {"id": "one", "label": "One"}))

        with pytest.raises(UnknownCommand):
            application.apply(diagram, DiagramCommand("add_relation", {"id": "bad"}))
        with pytest.raises(UnknownCommand):
            application.apply(
                diagram,
                DiagramCommand(
                    "add_relation",
                    {
                        "id": "syntax",
                        "source_id": "one",
                        "target_id": "one",
                        "relation_kind": "<|--",
                    },
                ),
            )
        with pytest.raises(RuntimeError, match=r"already exists"):
            application.apply(diagram, DiagramCommand("add_class", {"id": "one", "label": "Again"}))
        with pytest.raises(RuntimeError, match=r"unknown|does not exist"):
            application.apply(diagram, DiagramCommand("add_note", {"id": "note", "class_id": "missing", "text": "No"}))

    def test_empty_namespace_persists_as_a_draft_and_becomes_renderable_when_populated(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")
        application.execute(diagram, "add_namespace", {"id": "sales", "label": "Sales"})

        payload = application.snapshot(diagram).to_dict()
        restored = application.restore(json.loads(json.dumps(payload)))

        assert payload["draft"] is True
        assert not restored.validate().can_commit
        assert application.snapshot(restored).to_dict() == payload
        report = application.validate_render(restored)
        assert not report.success
        assert not report.svg
        assert report.diagnostics[0].code == "diagram_invalid"
        with pytest.raises(RuntimeError, match="requires a class"):
            application.render(restored)

        application.execute(restored, "add_class", {"id": "order", "label": "Order", "parent_id": "sales"})

        assert application.snapshot(restored).draft is False
        assert restored.validate().can_commit
        assert 'namespace c_v_sales["Sales"]' in application.render(restored)

    @pytest.mark.parametrize(
        "operation,arguments",
        (
            ("remove_element", {"id": "order"}),
            ("move_element", {"id": "order", "kind": "class", "parent_id": ""}),
        ),
    )
    def test_removing_the_last_namespace_child_is_rejected_without_losing_the_child(
        self, operation: str, arguments: dict[str, object]
    ) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")
        application.execute(diagram, "add_namespace", {"id": "sales", "label": "Sales"})
        application.execute(diagram, "add_class", {"id": "order", "label": "Order", "parent_id": "sales"})
        before = application.snapshot(diagram).to_dict()
        source = application.render(diagram)

        with pytest.raises(RuntimeError, match="requires a class"):
            application.execute(diagram, operation, arguments)

        assert application.snapshot(diagram).to_dict() == before
        assert application.render(diagram) == source
        application.execute(diagram, "add_class", {"id": "invoice", "label": "Invoice", "parent_id": "sales"})
        application.execute(diagram, operation, arguments)
        assert diagram.validate().can_commit
        assert diagram.find_element("invoice") is not None

    @pytest.mark.parametrize("operation", ("add_note", "update_annotation"))
    def test_a_note_cannot_target_a_namespace(self, operation: str) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")
        application.execute(diagram, "add_namespace", {"id": "sales", "label": "Sales"})
        application.execute(diagram, "add_class", {"id": "order", "label": "Order", "parent_id": "sales"})
        application.execute(diagram, "add_note", {"id": "note", "class_id": "order", "text": "Pay before shipping"})
        before = application.snapshot(diagram).to_dict()
        source = application.render(diagram)

        with pytest.raises(RuntimeError, match="class"):
            if operation == "add_note":
                application.execute(diagram, operation, {"id": "new", "class_id": "sales", "text": "Sales note"})
            else:
                application.execute(
                    diagram,
                    operation,
                    {
                        "id": "note",
                        "kind": "class_note",
                        "changes": {
                            "targets": [{"kind": "element", "id": "sales"}],
                        },
                    },
                )

        assert application.snapshot(diagram).to_dict() == before
        assert application.render(diagram) == source

    @pytest.mark.parametrize(
        "targets",
        (
            [],
            [{"kind": "element", "id": "order"}, {"kind": "element", "id": "invoice"}],
            [{"kind": "relation", "id": "billing"}],
        ),
    )
    def test_note_target_edits_reject_unsupported_cardinality_and_kinds(self, targets: list[dict[str, str]]) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")
        application.execute(diagram, "add_class", {"id": "order", "label": "Order"})
        application.execute(diagram, "add_class", {"id": "invoice", "label": "Invoice"})
        application.execute(diagram, "add_relation", {"id": "billing", "source_id": "order", "target_id": "invoice"})
        application.execute(diagram, "add_note", {"id": "note", "class_id": "order", "text": "Pay before shipping"})
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(RuntimeError):
            application.execute(
                diagram, "update_annotation", {"id": "note", "kind": "class_note", "changes": {"targets": targets}}
            )

        assert application.snapshot(diagram).to_dict() == before
        application.execute(
            diagram,
            "update_annotation",
            {
                "id": "note",
                "kind": "class_note",
                "changes": {
                    "targets": [{"kind": "element", "id": "invoice"}],
                },
            },
        )
        assert 'note for c_v_invoice "Pay before shipping"' in application.render(diagram)
        assert "note for c_v_order" not in application.render(diagram)

    @pytest.mark.parametrize("text", ("", " ", "Pay\nnow", "Pay\x00now"))
    @pytest.mark.parametrize("operation", ("add_note", "update_annotation"))
    def test_invalid_note_text_is_rejected_without_changing_existing_notes(self, text: str, operation: str) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")
        application.execute(diagram, "add_class", {"id": "order", "label": "Order"})
        application.execute(diagram, "add_note", {"id": "note", "class_id": "order", "text": "Pay before shipping"})
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(RuntimeError, match="text"):
            if operation == "add_note":
                application.execute(diagram, operation, {"id": "new", "class_id": "order", "text": text})
            else:
                application.execute(diagram, operation, {"id": "note", "kind": "class_note", "changes": {"text": text}})

        assert application.snapshot(diagram).to_dict() == before
