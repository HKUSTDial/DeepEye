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


def test_workflow_node_specs_include_builtin_transform_and_answer_nodes() -> None:
    node_types = {spec.type for spec in build_registry().all()}

    assert {"rows.select", "rows.filter", "rows.sort", "rows.aggregate", "rows.profile", "llm.answer"} <= node_types


def test_workflow_node_specs_hide_internal_or_legacy_params() -> None:
    specs = {spec.type: spec for spec in build_registry().all()}

    assert "datasource_url" not in (specs["datasource.read"].params_schema or {})
    assert "datasource_type" not in (specs["datasource.read"].params_schema or {})
    assert "datasource_url" not in (specs["sql.execute"].params_schema or {})
    assert "datasource_type" not in (specs["sql.execute"].params_schema or {})
    assert "code_path" not in (specs["python.code"].params_schema or {})
    assert "code_b64" not in (specs["python.code"].params_schema or {})
    assert "workdir" not in (specs["python.code"].params_schema or {})
    assert "nulls_last" not in (specs["rows.sort"].params_schema or {})
    assert "sample_size" not in (specs["rows.profile"].params_schema or {})
    assert "file_paths" not in (specs["report.generate"].params_schema or {})
    assert "template" not in (specs["report.generate"].params_schema or {})
    assert "output_path" not in (specs["report.generate"].params_schema or {})
    assert "model" not in (specs["data.generate_dashboard"].params_schema or {})
    assert "data" not in (specs["data.generate_dashboard"].params_schema or {})
    assert "datasource_id" not in (specs["data.generate_dashboard"].params_schema or {})
    assert "data_schema" not in (specs["data.generate_dashboard"].params_schema or {})
    assert "workers" not in (specs["video.generator"].params_schema or {})
    assert "instructions" not in (specs["llm.answer"].params_schema or {})
