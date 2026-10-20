from autosar_rag.validator import ConsistencyValidator


def test_port_order_does_not_mark_component_modified():
    old = {"components": [{"name": "CompA", "ports": [
        {"name": "P1", "direction": "provided", "interface_name": "IfA"},
        {"name": "P2", "direction": "required", "interface_name": "IfB"},
    ]}]}
    new = {"components": [{"name": "CompA", "ports": [
        {"name": "P2", "direction": "required", "interface_name": "IfB"},
        {"name": "P1", "direction": "provided", "interface_name": "IfA"},
    ]}]}
    diff = ConsistencyValidator.compare_revisions(old, new)
    assert diff["modified_components"] == []
    assert diff["changes"] == []


def test_port_interface_change_is_field_level():
    old = {"components": [{"name": "CompA", "ports": [
        {"name": "P1", "direction": "provided", "interface_name": "IfA"}
    ]}]}
    new = {"components": [{"name": "CompA", "ports": [
        {"name": "P1", "direction": "provided", "interface_name": "IfB"}
    ]}]}
    diff = ConsistencyValidator.compare_revisions(old, new)
    assert diff["modified_components"] == ["CompA"]
    assert any("interface_name" in change["path"] for change in diff["changes"])


def test_component_port_changes_and_dependencies_are_reported():
    old = {
        "components": [{"name": "CompA", "ports": []}],
        "dependencies": [{"source_entity": "CompA", "target_entity": "CompB", "relationship": "uses"}],
    }
    new = {
        "components": [{"name": "CompA", "ports": [{"name": "P1", "direction": "required"}]}],
        "dependencies": [{"source_entity": "CompA", "target_entity": "CompC", "relationship": "uses"}],
    }
    diff = ConsistencyValidator.compare_revisions(old, new)
    assert "CompA" in diff["modified_components"]
    assert len(diff["added_dependencies"]) == 1
    assert len(diff["removed_dependencies"]) == 1
    assert any("ports" in change["path"] for change in diff["changes"])


def test_validation_accepts_interface_name_alias_and_attaches_evidence():
    model = {
        "components": [{
            "name": "CompA",
            "evidence": [{"source": "HLD.pdf", "page_number": 3}],
            "ports": [{"name": "P1", "direction": "provided", "interface_name": "IfA",
                       "evidence": [{"source": "HLD.pdf", "page_number": 4}]}],
        }],
        "interfaces": [{"name": "IfA"}],
        "signals": [],
        "dependencies": [],
    }
    findings = ConsistencyValidator.validate_model(model)
    assert not any(f["rule_id"] == "PORT_INTERFACE_UNRESOLVED" for f in findings)
    assert not any(f["rule_id"] == "PORT_INTERFACE_NOT_IN_INVENTORY" for f in findings)


def test_validation_flags_unresolved_interface_as_review_not_compliance_failure():
    model = {"components": [{"name": "CompA", "ports": [{"name": "P1"}]}]}
    findings = ConsistencyValidator.validate_model(model)
    finding = next(f for f in findings if f["rule_id"] == "PORT_INTERFACE_UNRESOLVED")
    assert finding["status"] == "needs_review"
    assert finding["severity"] == "warning"
