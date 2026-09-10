"""Geometry and answer-schema builders shared by student and admin routes.

Both the student problem route and the admin preview route need to build the same
wire payload from a generator's ``ProblemDisplayData``.  Having a single
implementation here prevents the two from drifting (which previously resulted in
the admin preview returning an empty truss-shaped geometry for rigid-body slots).
"""

from typing import Any

_SUBSCRIPT_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def member_field_key(member_id: int) -> str:
    """Answer-field key for a truss member, e.g. 1 -> 'S1'. Stable across releases."""
    return f"S{member_id}"


def _member_label(member_id: int) -> str:
    return "S" + str(member_id).translate(_SUBSCRIPT_DIGITS)


def _force_label(magnitude: float) -> str:
    """Display label for a point load, e.g. 3 -> '3F' and 1 -> 'F'."""
    rounded = round(magnitude, 4)
    if abs(rounded - 1.0) < 1e-9:
        return "F"
    whole = int(rounded)
    return f"{whole}F" if abs(rounded - whole) < 1e-9 else f"{rounded:g}F"


def build_truss_geometry(visual_schema: list[Any]) -> dict[str, Any]:
    """Translate generator primitives into the contract's TrussGeometry shape.

    Node and member ids are 1-based on the wire; the generator emits 0-based
    node indices, so every node reference is offset by one here.
    """
    nodes, members, supports, forces = [], [], [], []
    member_idx = 0
    for el in visual_schema:
        p = el.properties
        t = el.element_type
        if t == "node":
            nodes.append({"id": int(p["id"]) + 1, "x": p["x"], "y": p["y"]})
        elif t == "member":
            member_idx += 1
            members.append(
                {
                    "id": member_idx,
                    "from": int(p["start_node"]) + 1,
                    "to": int(p["end_node"]) + 1,
                    "label": _member_label(member_idx),
                }
            )
        elif t in ("pin", "roller"):
            supports.append(
                {
                    "node": int(p["node_index"]) + 1,
                    "type": t,
                    "angleDeg": int(p.get("rotation", 0)),
                }
            )
        elif t == "point_load":
            fv = p["force_vector"]
            mag = (fv[0] ** 2 + fv[1] ** 2) ** 0.5
            forces.append(
                {
                    "node": int(p["node_index"]) + 1,
                    "fx": float(fv[0]),
                    "fy": float(fv[1]),
                    "label": _force_label(mag),
                }
            )

    if nodes:
        xs = [n["x"] for n in nodes]
        ys = [n["y"] for n in nodes]
        pad_x = max((max(xs) - min(xs)) * 0.15, 1.0)
        pad_y = max((max(ys) - min(ys)) * 0.15, 1.0)
        bounds = {
            "xMin": min(xs) - pad_x,
            "xMax": max(xs) + pad_x,
            "yMin": min(ys) - pad_y,
            "yMax": max(ys) + pad_y,
        }
    else:
        bounds = {"xMin": -1, "xMax": 1, "yMin": -1, "yMax": 1}

    return {
        "schemaVersion": 1,
        "nodes": nodes,
        "members": members,
        "supports": supports,
        "forces": forces,
        "bounds": bounds,
    }


def build_answer_schema_truss(members: list[dict[str, Any]]) -> dict[str, Any]:
    """Answer schema for a truss slot (member-force fields keyed S1…Sn)."""
    fields = [
        {
            "key": member_field_key(m["id"]),
            "label": m["label"],
            "unit": "F",
            "type": "number",
            "decimals": 2,
        }
        for m in members
    ]
    return {"groups": [{"id": "member-forces", "label": "Member Forces", "fields": fields}]}


def build_display_payload(problem_type: str, display: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (geometry, answer_schema) ready to place in a ProblemPayload.

    ``truss`` keeps its bespoke path because its answer schema is derived from
    member ids rather than the generator-declared ``answer_schema``.  Every
    other type uses the generic generator-declared path.

    The ``type`` field is pinned to the contract's ``"number"`` enum rather than
    forwarded from ``AnswerFieldSpec.value_type`` (which says ``"numeric"``).
    """
    if problem_type == "truss":
        geometry = build_truss_geometry(display.visual_schema)
        return geometry, build_answer_schema_truss(geometry["members"])

    geometry = {
        "schemaVersion": 1,
        "elements": [el.model_dump() for el in display.visual_schema],
    }
    answer_schema = {
        "groups": [
            {
                "id": "answers",
                "label": "Answers",
                "fields": [
                    {
                        "key": f.field_id,
                        "label": f.label,
                        "unit": f.unit,
                        "type": "number",
                        "decimals": 2,
                    }
                    for f in display.answer_schema
                ],
            }
        ]
    }
    return geometry, answer_schema
