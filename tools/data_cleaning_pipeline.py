#!/usr/bin/env python3
"""XML-first (XML-only rooms) data cleaning pipeline for course scheduling."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List
import xml.etree.ElementTree as ET

REQUIRED_COURSE_COLS = [
    "course_id",
    "course_name",
    "enrollment",
    "weekly_hours",
    "teacher_id",
    "dept",
    "course_type",
]
REQUIRED_ROOM_COLS = ["room_id", "capacity", "room_type", "building", "available_slots"]
REQUIRED_TEACHER_COLS = ["teacher_id", "teacher_name", "dept", "max_weekly_hours"]


def parse_int(v: object, default: int = 0) -> int:
    try:
        return int(float(str(v).strip()))
    except Exception:
        return default


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def text_of(el: ET.Element, names: List[str]) -> str:
    for name in names:
        if name == "@id":
            v = el.attrib.get("id", "").strip()
        else:
            child = el.find(name)
            v = "" if child is None or child.text is None else child.text.strip()
        if v:
            return v
    return ""


def parse_xml_entities(xml_path: Path, default_slots: int) -> Dict[str, List[Dict[str, object]]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    courses: List[Dict[str, object]] = []
    for el in root.findall(".//course") + root.findall(".//Course"):
        cid = text_of(el, ["id", "course_id", "@id"])
        if not cid:
            continue
        enrollment = parse_int(text_of(el, ["enrollment", "students", "size"]), 0)
        weekly_hours = parse_int(text_of(el, ["weekly_hours", "hours", "periods"]), 0)
        if enrollment <= 0 or weekly_hours <= 0:
            continue
        courses.append(
            {
                "course_id": cid,
                "course_name": text_of(el, ["name", "course_name"]) or cid,
                "enrollment": enrollment,
                "weekly_hours": weekly_hours,
                "teacher_id": text_of(el, ["teacher_id", "teacher", "instructor"]) or f"TBD_{cid}",
                "dept": text_of(el, ["dept", "department"]) or "UNASSIGNED",
                "course_type": (text_of(el, ["course_type", "type"]) or "LECTURE").upper(),
            }
        )

    rooms: List[Dict[str, object]] = []
    for el in root.findall(".//room") + root.findall(".//Room") + root.findall(".//classroom"):
        rid = text_of(el, ["id", "room_id", "@id"])
        if not rid:
            continue
        capacity = parse_int(text_of(el, ["capacity", "size"]), 0)
        if capacity <= 0:
            continue
        slots = parse_int(text_of(el, ["available_slots", "slots", "available"]), default_slots)
        if slots <= 0:
            slots = default_slots
        rooms.append(
            {
                "room_id": rid,
                "capacity": capacity,
                "room_type": (text_of(el, ["room_type", "type"]) or "LECTURE").upper(),
                "building": text_of(el, ["building", "campus"]) or "UNKNOWN",
                "available_slots": slots,
            }
        )

    teachers: List[Dict[str, object]] = []
    for el in root.findall(".//teacher") + root.findall(".//Teacher") + root.findall(".//instructor"):
        tid = text_of(el, ["id", "teacher_id", "@id"])
        if not tid:
            continue
        teachers.append(
            {
                "teacher_id": tid,
                "teacher_name": text_of(el, ["name", "teacher_name"]) or tid,
                "dept": text_of(el, ["dept", "department"]) or "UNASSIGNED",
                "max_weekly_hours": parse_int(text_of(el, ["max_weekly_hours", "max_hours"]), 12),
            }
        )

    return {"courses": courses, "rooms": rooms, "teachers": teachers}


def build_teacher_table(courses, xml_teachers):
    known = {str(t["teacher_id"]): dict(t) for t in xml_teachers}
    for c in courses:
        tid = str(c["teacher_id"])
        if tid not in known:
            known[tid] = {
                "teacher_id": tid,
                "teacher_name": "待补充" if tid.startswith("TBD_") else tid,
                "dept": str(c["dept"]),
                "max_weekly_hours": 12,
            }
    return sorted(known.values(), key=lambda x: x["teacher_id"])


def diagnostics(courses, rooms):
    demand = sum(int(c["weekly_hours"]) for c in courses)
    supply = sum(int(r["available_slots"]) for r in rooms)
    ratio = demand / supply if supply else 0.0
    caps = [int(r["capacity"]) for r in rooms]
    feasible = sum(1 for c in courses if any(cap >= int(c["enrollment"]) for cap in caps))
    teacher_complete = sum(1 for c in courses if not str(c["teacher_id"]).startswith("TBD_"))
    return {
        "courses": len(courses),
        "rooms": len(rooms),
        "demand_hours": demand,
        "supply_hours": supply,
        "demand_supply_ratio": round(ratio, 4),
        "capacity_feasible_ratio": round(feasible / len(courses), 4) if courses else 0.0,
        "teacher_complete_ratio": round(teacher_complete / len(courses), 4) if courses else 0.0,
    }


def recommend_room_scale(courses: List[Dict[str, object]], target_utilization: float) -> Dict[str, int]:
    total_enrollment = sum(int(c["enrollment"]) for c in courses)
    avg_enrollment = max(1, round(total_enrollment / len(courses))) if courses else 1
    suggested_capacity = max(40, ((avg_enrollment + 9) // 10) * 10)
    weekly_demand = sum(int(c["weekly_hours"]) for c in courses)
    per_room_slots = 50
    suggested_rooms = max(1, int((weekly_demand / max(0.1, target_utilization)) / per_room_slots + 0.999))
    return {
        "suggested_room_count": suggested_rooms,
        "suggested_room_capacity": suggested_capacity,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--xml", required=True, help="XML source file")
    p.add_argument("--out", required=True)
    p.add_argument("--default-slots", type=int, default=50)
    p.add_argument("--target-utilization", type=float, default=0.75)
    args = p.parse_args()

    xml_data = parse_xml_entities(Path(args.xml), args.default_slots)
    courses = xml_data["courses"]
    rooms = xml_data["rooms"]
    teachers = build_teacher_table(courses, xml_data["teachers"])

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    write_csv(out / "cleaned_courses.csv", courses, REQUIRED_COURSE_COLS)
    write_csv(out / "cleaned_rooms.csv", rooms, REQUIRED_ROOM_COLS)
    write_csv(out / "cleaned_teachers.csv", teachers, REQUIRED_TEACHER_COLS)
    report = diagnostics(courses, rooms)
    report["room_recommendation"] = recommend_room_scale(courses, args.target_utilization)
    with (out / "diagnostic_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
