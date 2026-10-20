from autosar_rag.structured_extractor import (
    StructuredExtractor,
    _attach_evidence,
    _extract_json_object,
    _validate_raw_model,
    EMPTY_MODEL,
)


def test_json_extractor_accepts_fenced_json_with_prefix():
    raw = _extract_json_object('Result follows:\n```json\n{"components": []}\n```')
    assert raw == {"components": []}


def test_extractor_contract_requires_all_top_level_arrays():
    try:
        _validate_raw_model({"components": []})
    except ValueError as exc:
        assert "missing required arrays" in str(exc)
    else:
        raise AssertionError("Incomplete extraction object was accepted")


def test_extractor_contract_rejects_dependency_without_endpoint():
    raw = {key: [] for key in EMPTY_MODEL}
    raw["dependencies"] = [{"source_entity": "A", "target_entity": ""}]
    try:
        _validate_raw_model(raw)
    except ValueError as exc:
        assert "missing an endpoint" in str(exc)
    else:
        raise AssertionError("Invalid dependency was accepted")


def test_evidence_is_attached_recursively_to_nested_entities():
    model = {
        "components": [{"name": "A", "ports": [{"name": "P", "signals": [{"name": "S"}]}]}],
        "interfaces": [{"name": "If", "signals": [{"name": "S2"}]}],
        "signals": [], "functional_flows": [], "dependencies": [],
    }
    evidence = {"source": "HLD.pdf", "page_number": 3, "chunk_id": "c-1"}
    result = _attach_evidence(model, evidence)
    assert result["components"][0]["evidence"] == [evidence]
    assert result["components"][0]["ports"][0]["evidence"] == [evidence]
    assert result["components"][0]["ports"][0]["signals"][0]["evidence"] == [evidence]
    assert result["interfaces"][0]["signals"][0]["evidence"] == [evidence]


def test_merge_keeps_nested_signals_and_prefers_known_port_direction():
    extractor = object.__new__(StructuredExtractor)
    evidence1 = {"source": "v1.pdf", "page_number": 1}
    evidence2 = {"source": "v1.pdf", "page_number": 2}
    first = {
        "components": [{"name": "CompA", "ports": [{
            "name": "P1", "direction": "unknown", "interface_name": None,
            "signals": [{"name": "SignalA", "data_type": "uint8", "evidence": [evidence1]}],
            "evidence": [evidence1],
        }]}],
        "interfaces": [], "signals": [], "functional_flows": [], "dependencies": [],
    }
    second = {
        "components": [{"name": "compa", "ports": [{
            "name": "P1", "direction": "provided", "interface_name": "IfA",
            "signals": [{"name": "SignalB", "data_type": "uint16", "evidence": [evidence2]}],
            "evidence": [evidence2],
        }]}],
        "interfaces": [], "signals": [], "functional_flows": [], "dependencies": [],
    }
    result = extractor.merge_extractions([first, second])
    component = result["components"][0]
    assert len(result["components"]) == 1
    assert len(component["ports"]) == 1
    port = component["ports"][0]
    assert port["direction"] == "provided"
    assert port["interface_name"] == "IfA"
    assert {s["name"] for s in port["signals"]} == {"SignalA", "SignalB"}
    assert len(port["evidence"]) == 2
