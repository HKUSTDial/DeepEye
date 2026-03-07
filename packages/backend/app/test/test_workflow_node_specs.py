from app.services.workflow_engine import build_registry


def test_workflow_node_specs_serialize_schema_with_public_alias() -> None:
    specs = [spec.model_dump(mode="json", by_alias=True) for spec in build_registry().all()]

    assert specs
    for spec in specs:
        for port_group in ("inputs", "outputs"):
            for port in spec.get(port_group, {}).values():
                assert "schema_" not in port
                if port:
                    assert "schema" in port or not port


def test_workflow_node_specs_include_version() -> None:
    specs = build_registry().all()

    assert specs
    assert all(spec.version for spec in specs)
