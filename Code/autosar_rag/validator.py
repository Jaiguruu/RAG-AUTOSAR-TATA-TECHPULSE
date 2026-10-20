"""Evidence-aware validation and order-insensitive model revision comparison.

Validation findings are potential gaps in the extracted model, not formal
AUTOSAR compliance judgments. Missing extraction data must not be presented as
proof that the source document is incorrect.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any, Dict, List, Optional


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _evidence(entity: Dict[str, Any]) -> List[Dict[str, Any]]:
    value = entity.get("evidence", [])
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _add_finding(
    findings: List[Dict[str, Any]],
    *,
    rule_id: str,
    severity: str,
    entity: str,
    issue: str,
    evidence: Optional[List[Dict[str, Any]]] = None,
    status: str = "needs_review",
) -> None:
    findings.append({
        "rule_id": rule_id,
        "severity": severity,
        "entity": entity,
        # Retain legacy keys used by the current Streamlit UI.
        "component": entity,
        "issue": issue,
        "evidence": evidence or [],
        "status": status,
    })


def _name_map(items: Any) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    if not isinstance(items, list):
        return result
    for item in items:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        key = _norm(item["name"])
        if key:
            result.setdefault(key, item)
    return result


_UNORDERED_COLLECTION_FIELDS = {"components", "ports", "interfaces", "signals", "dependencies"}


def _canonical(value: Any, *, sort_this_list: bool = False) -> Any:
    """Canonicalize unordered entity collections without reordering workflows."""
    if isinstance(value, dict):
        normalized = {}
        for key, item in sorted(value.items()):
            if key in {"evidence", "source", "page_number", "page_start", "page_end"}:
                continue
            normalized[key] = _canonical(item, sort_this_list=key in _UNORDERED_COLLECTION_FIELDS)
        return normalized
    if isinstance(value, list):
        values = [_canonical(item) for item in value]
        if sort_this_list:
            return sorted(values, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
        return values
    return value


def _field_diffs(old: Dict[str, Any], new: Dict[str, Any], path: str) -> List[Dict[str, Any]]:
    diffs: List[Dict[str, Any]] = []
    old_keys, new_keys = set(old), set(new)
    ignored = {"evidence", "source", "page_number", "page_start", "page_end"}
    for key in sorted((old_keys | new_keys) - ignored):
        old_value = old.get(key)
        new_value = new.get(key)
        field_path = f"{path}.{key}" if path else key
        if key not in old:
            diffs.append({"path": field_path, "old": None, "new": copy.deepcopy(new_value), "change_type": "added"})
        elif key not in new:
            diffs.append({"path": field_path, "old": copy.deepcopy(old_value), "new": None, "change_type": "removed"})
        elif _canonical(old_value) != _canonical(new_value):
            if isinstance(old_value, dict) and isinstance(new_value, dict):
                nested = _field_diffs(old_value, new_value, field_path)
                diffs.extend(nested or [{"path": field_path, "old": old_value, "new": new_value, "change_type": "modified"}])
            else:
                diffs.append({"path": field_path, "old": copy.deepcopy(old_value), "new": copy.deepcopy(new_value), "change_type": "modified"})
    return diffs


def _identity(item: Dict[str, Any]) -> str:
    if item.get("name"):
        return _norm(item.get("name"))
    return "|".join(_norm(item.get(key)) for key in ("source_entity", "source", "target_entity", "target", "relationship", "type"))


def _deep_diff(old: Any, new: Any, path: str) -> List[Dict[str, Any]]:
    """Return field-level differences, comparing named entity lists by identity."""
    if isinstance(old, dict) and isinstance(new, dict):
        differences: List[Dict[str, Any]] = []
        ignored = {"evidence", "source", "page_number", "page_start", "page_end"}
        for key in sorted((set(old) | set(new)) - ignored):
            field_path = f"{path}.{key}" if path else key
            if key not in old:
                differences.append({"path": field_path, "old": None, "new": copy.deepcopy(new[key]), "change_type": "added"})
            elif key not in new:
                differences.append({"path": field_path, "old": copy.deepcopy(old[key]), "new": None, "change_type": "removed"})
            else:
                differences.extend(_deep_diff(old[key], new[key], field_path))
        return differences

    if isinstance(old, list) and isinstance(new, list):
        last_key = path.rsplit(".", 1)[-1]
        if last_key in _UNORDERED_COLLECTION_FIELDS and all(isinstance(x, dict) and _identity(x) for x in old + new):
            old_map = {_identity(x): x for x in old}
            new_map = {_identity(x): x for x in new}
            differences: List[Dict[str, Any]] = []
            for key in sorted(set(old_map) - set(new_map)):
                differences.append({"path": f"{path}[{key}]", "old": copy.deepcopy(old_map[key]), "new": None, "change_type": "removed"})
            for key in sorted(set(new_map) - set(old_map)):
                differences.append({"path": f"{path}[{key}]", "old": None, "new": copy.deepcopy(new_map[key]), "change_type": "added"})
            for key in sorted(set(old_map) & set(new_map)):
                differences.extend(_deep_diff(old_map[key], new_map[key], f"{path}[{key}]"))
            return differences
        if _canonical(old) == _canonical(new):
            return []
        return [{"path": path, "old": copy.deepcopy(old), "new": copy.deepcopy(new), "change_type": "modified"}]

    if _canonical(old) == _canonical(new):
        return []
    return [{"path": path, "old": copy.deepcopy(old), "new": copy.deepcopy(new), "change_type": "modified"}]


class ConsistencyValidator:
    """Run conservative structural checks against an extracted architecture model."""

    @staticmethod
    def validate_model(model: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        if not isinstance(model, dict):
            return [{
                "rule_id": "INVALID_ARCHITECTURE_MODEL",
                "severity": "error",
                "entity": "architecture model",
                "component": "architecture model",
                "issue": "Architecture model must be a JSON object.",
                "evidence": [],
                "status": "needs_review",
            }]

        collection_names = ("components", "interfaces", "signals", "functional_flows", "dependencies")
        for collection_name in collection_names:
            if collection_name in model and not isinstance(model[collection_name], list):
                _add_finding(
                    findings, rule_id="INVALID_MODEL_COLLECTION", severity="error",
                    entity=collection_name, issue=f"Model field {collection_name!r} must be a list."
                )
        components = model.get("components", [])
        interfaces = model.get("interfaces", [])
        signals = model.get("signals", [])
        flows = model.get("functional_flows", [])
        dependencies = model.get("dependencies", [])
        interface_map = _name_map(interfaces)
        component_map = _name_map(components)
        signal_map = _name_map(signals)
        flow_map = _name_map(flows)
        all_entity_names = set(component_map) | set(interface_map) | set(signal_map) | set(flow_map)
        for component in components if isinstance(components, list) else []:
            if not isinstance(component, dict) or not component.get("name"):
                continue
            component_name = str(component["name"])
            for port in component.get("ports", []) if isinstance(component.get("ports", []), list) else []:
                if isinstance(port, dict) and port.get("name"):
                    all_entity_names.add(_norm(f"{component_name}.{port['name']}"))

        # Duplicate top-level names are often extraction/merge problems. Report
        # them as review warnings rather than assuming the source is invalid.
        for collection_name, records in (("interfaces", interfaces), ("signals", signals), ("functional_flows", flows)):
            names_seen: set[str] = set()
            for record in records if isinstance(records, list) else []:
                if not isinstance(record, dict) or not record.get("name"):
                    continue
                key = _norm(record["name"])
                if key in names_seen:
                    _add_finding(
                        findings, rule_id=f"DUPLICATE_{collection_name.upper()[:-1]}", severity="warning",
                        entity=str(record["name"]),
                        issue=f"Multiple {collection_name.replace('_', ' ')} records share this normalized name; review entity resolution.",
                        evidence=_evidence(record),
                    )
                names_seen.add(key)

        component_seen: set[str] = set()
        for comp in components if isinstance(components, list) else []:
            if not isinstance(comp, dict):
                _add_finding(findings, rule_id="INVALID_COMPONENT_RECORD", severity="error", entity="unknown", issue="Component record is not an object.")
                continue
            name = str(comp.get("name") or "Unknown")
            key = _norm(name)
            if not comp.get("name"):
                _add_finding(findings, rule_id="COMPONENT_NAME_MISSING", severity="error", entity=name, issue="Component has no name.", evidence=_evidence(comp))
            elif key in component_seen:
                _add_finding(findings, rule_id="DUPLICATE_COMPONENT", severity="warning", entity=name, issue="Multiple component records share this normalized name; review entity resolution.", evidence=_evidence(comp))
            component_seen.add(key)

            ports = comp.get("ports", [])
            if not isinstance(ports, list):
                _add_finding(findings, rule_id="INVALID_PORT_LIST", severity="error", entity=name, issue="Component ports field must be a list.", evidence=_evidence(comp))
                ports = []
            if not ports:
                _add_finding(
                    findings, rule_id="NO_PORTS_EXTRACTED", severity="warning", entity=name,
                    issue="No ports were extracted for this component. Confirm whether the source defines none or extraction missed them.",
                    evidence=_evidence(comp),
                )
            port_seen: set[str] = set()
            for port in ports:
                if not isinstance(port, dict):
                    _add_finding(findings, rule_id="INVALID_PORT_RECORD", severity="error", entity=name, issue="Port record is not an object.", evidence=_evidence(comp))
                    continue
                port_name = str(port.get("name") or "Unknown port")
                port_key = _norm(port_name)
                if port_key in port_seen:
                    _add_finding(findings, rule_id="DUPLICATE_PORT", severity="warning", entity=f"{name}.{port_name}", issue="Duplicate port name within component; verify direction and interface.", evidence=_evidence(port) or _evidence(comp))
                port_seen.add(port_key)
                direction = _norm(port.get("direction"))
                if direction not in {"provided", "required", "unknown"}:
                    _add_finding(findings, rule_id="INVALID_PORT_DIRECTION", severity="warning", entity=f"{name}.{port_name}", issue=f"Unrecognized port direction: {direction!r}.", evidence=_evidence(port))
                interface_name = port.get("interface_name", port.get("interface"))
                if not interface_name:
                    _add_finding(
                        findings, rule_id="PORT_INTERFACE_UNRESOLVED", severity="warning", entity=f"{name}.{port_name}",
                        issue="Port interface is absent from the extracted model; this may reflect missing source evidence rather than a source defect.",
                        evidence=_evidence(port) or _evidence(comp),
                    )
                elif interface_map and _norm(interface_name) not in interface_map:
                    _add_finding(
                        findings, rule_id="PORT_INTERFACE_NOT_IN_INVENTORY", severity="warning", entity=f"{name}.{port_name}",
                        issue=f"Port references interface {interface_name!r}, which is not present in the extracted interface inventory.",
                        evidence=_evidence(port) or _evidence(comp),
                    )

        for dependency in dependencies if isinstance(dependencies, list) else []:
            if not isinstance(dependency, dict):
                continue
            source = str(dependency.get("source_entity", dependency.get("source", ""))).strip()
            target = str(dependency.get("target_entity", dependency.get("target", ""))).strip()
            if not source or not target:
                _add_finding(findings, rule_id="DEPENDENCY_ENDPOINT_MISSING", severity="warning", entity="dependency", issue="Dependency is missing a source or target endpoint.", evidence=_evidence(dependency))
                continue
            # Only flag unresolved names when there is a meaningful entity inventory.
            if all_entity_names and (_norm(source) not in all_entity_names or _norm(target) not in all_entity_names):
                unresolved = [value for value in (source, target) if _norm(value) not in all_entity_names]
                _add_finding(findings, rule_id="DEPENDENCY_ENDPOINT_UNRESOLVED", severity="warning", entity=f"{source} -> {target}", issue=f"Dependency endpoint(s) are absent from extracted inventories: {', '.join(unresolved)}. Review entity coverage before treating this as an architecture error.", evidence=_evidence(dependency))

        return findings

    @staticmethod
    def compare_revisions(old_model: Dict[str, Any], new_model: Dict[str, Any]) -> Dict[str, Any]:
        """Compare model entities semantically, ignoring source evidence and list order.

        Legacy added_components/removed_components/modified_components fields are
        retained for the existing UI; ``changes`` provides field-level detail.
        """
        diff: Dict[str, Any] = {
            "added_components": [], "removed_components": [], "modified_components": [],
            "added_interfaces": [], "removed_interfaces": [], "modified_interfaces": [],
            "added_signals": [], "removed_signals": [], "modified_signals": [],
            "added_functional_flows": [], "removed_functional_flows": [], "modified_functional_flows": [],
            "added_dependencies": [], "removed_dependencies": [],
            "changes": [],
        }

        def compare_named(kind: str, old_items: Any, new_items: Any, name_field: str = "name", nested_fields: tuple[str, ...] = ()) -> None:
            old_map = _name_map(old_items)
            new_map = _name_map(new_items)
            diff[f"added_{kind}"].extend(new_map[k][name_field] for k in sorted(set(new_map) - set(old_map)))
            diff[f"removed_{kind}"].extend(old_map[k][name_field] for k in sorted(set(old_map) - set(new_map)))
            for key in sorted(set(old_map) & set(new_map)):
                old_item = old_map[key]
                new_item = new_map[key]
                entity_name = old_item.get(name_field, key)
                changed = _deep_diff(old_item, new_item, str(entity_name))
                if changed:
                    diff[f"modified_{kind}"].append(entity_name)
                    for change in changed:
                        change["entity_type"] = kind[:-1] if kind.endswith("s") else kind
                        change["entity"] = entity_name
                        change["old_evidence"] = copy.deepcopy(_evidence(old_item))
                        change["new_evidence"] = copy.deepcopy(_evidence(new_item))
                    diff["changes"].extend(changed)

        compare_named("components", old_model.get("components", []), new_model.get("components", []))
        compare_named("interfaces", old_model.get("interfaces", []), new_model.get("interfaces", []))
        compare_named("signals", old_model.get("signals", []), new_model.get("signals", []))
        compare_named("functional_flows", old_model.get("functional_flows", []), new_model.get("functional_flows", []))

        def dep_key(dep: Dict[str, Any]) -> tuple[str, str, str]:
            return (
                _norm(dep.get("source_entity", dep.get("source"))),
                _norm(dep.get("target_entity", dep.get("target"))),
                _norm(dep.get("relationship", dep.get("type"))),
            )

        old_deps = {dep_key(d): d for d in old_model.get("dependencies", []) if isinstance(d, dict)}
        new_deps = {dep_key(d): d for d in new_model.get("dependencies", []) if isinstance(d, dict)}
        diff["added_dependencies"] = [copy.deepcopy(new_deps[k]) for k in sorted(set(new_deps) - set(old_deps))]
        diff["removed_dependencies"] = [copy.deepcopy(old_deps[k]) for k in sorted(set(old_deps) - set(new_deps))]
        diff["changes"].sort(key=lambda item: (str(item.get("path", "")), str(item.get("change_type", ""))))
        return diff
