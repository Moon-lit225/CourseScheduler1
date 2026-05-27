#!/usr/bin/env python3
"""Purdue/ITC XML cleaning pipeline (XML-only room source)."""

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


def parse_purdue_xml(xml_path: Path) -> Dict[str, List[Dict[str, object]]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    nr_days = parse_int(root.attrib.get("nrDays", 5), 5)
    slots_per_day = parse_int(root.attrib.get("slotsPerDay", 288), 288)

    rooms: List[Dict[str, object]] = []
    for r in root.findall(".//rooms/room"):
        room_id = r.attrib.get("id", "").strip()
        cap = parse_int(r.attrib.get("capacity", 0), 0)
        if not room_id or cap <= 0:
            continue
        sharing_pattern = r.find("sharing/pattern")
        if sharing_pattern is not None and sharing_pattern.text:
            pattern = sharing_pattern.text.strip()
            available_slots = sum(1 for ch in pattern if ch != "X")
        else:
            available_slots = nr_days * 24  # 2-hour teaching blocks/day fallback
        rooms.append(
            {
                "room_id": room_id,
                "capacity": cap,
                "room_type": "LECTURE",
                "building": r.attrib.get("location", "UNKNOWN"),
                "available_slots": available_slots,
            }
        )

    courses: List[Dict[str, object]] = []
    teachers_map: Dict[str, Dict[str, object]] = {}
    for cls in root.findall(".//classes/class"):
        class_id = cls.attrib.get("id", "").strip()
        if not class_id:
            continue
        enrollment = parse_int(cls.attrib.get("classLimit", 0), 0)
        if enrollment <= 0:
            continue
        times = cls.findall("time")
        # estimate weekly hours from all candidate time options (avg length), length unit=5 minutes
        lengths = [parse_int(t.attrib.get("length", 0), 0) for t in times if parse_int(t.attrib.get("length", 0), 0) > 0]
        if lengths:
            weekly_hours = max(1, round((sum(lengths) / len(lengths)) * 5 / 60))
        else:
            weekly_hours = 2

        instructor_ids = [i.attrib.get("id", "").strip() for i in cls.findall("instructor") if i.attrib.get("id")]
        scheduler_id = cls.attrib.get("scheduler", "").strip()
        if scheduler_id:
            instructor_ids = [scheduler_id] + [x for x in instructor_ids if x != scheduler_id]
        teacher_id = instructor_ids[0] if instructor_ids else f"TBD_{class_id}"
        for tid in instructor_ids:
            teachers_map.setdefault(
                tid,
                {"teacher_id": tid, "teacher_name": f"I_{tid}", "dept": "UNASSIGNED", "max_weekly_hours": 12},
            )

        offering = cls.attrib.get("offering", "")
        subpart = cls.attrib.get("subpart", "")
        course_name = f"offering_{offering}_subpart_{subpart}" if offering or subpart else f"class_{class_id}"
        courses.append(
            {
                "course_id": class_id,
                "course_name": course_name,
                "enrollment": enrollment,
                "weekly_hours": weekly_hours,
                "teacher_id": teacher_id,
                "dept": "UNASSIGNED",
                "course_type": "LECTURE",
            }
        )

    for c in courses:
        tid = str(c["teacher_id"])
        if tid not in teachers_map:
            teachers_map[tid] = {
                "teacher_id": tid,
                "teacher_name": "待补充" if tid.startswith("TBD_") else f"I_{tid}",
                "dept": "UNASSIGNED",
                "max_weekly_hours": 12,
            }

    teachers = sorted(teachers_map.values(), key=lambda x: str(x["teacher_id"]))
    return {"courses": courses, "rooms": rooms, "teachers": teachers}


def diagnostics(courses, rooms):
    demand = sum(int(c["weekly_hours"]) for c in courses)
    supply = sum(int(r["available_slots"]) for r in rooms)
    ratio = demand / supply if supply else 0.0
    caps = [int(r["capacity"]) for r in rooms]
    feasible = sum(1 for c in courses if any(cap >= int(c["enrollment"]) for cap in caps))
    teacher_complete = sum(1 for c in courses if not str(c["teacher_id"]).startswith("TBD_"))
    teacher_ratio = (teacher_complete / len(courses)) if courses else 0.0
    return {
        "courses": len(courses),
        "rooms": len(rooms),
        "demand_hours": demand,
        "supply_hours": supply,
        "demand_supply_ratio": round(ratio, 6),
        "capacity_feasible_ratio": round(feasible / len(courses), 6) if courses else 0.0,
        "teacher_complete_ratio": round(teacher_ratio, 6),
        "risk_flags": {
            "oversubscribed": ratio > 0.85,
            "capacity_mismatch": (feasible / len(courses) if courses else 1.0) < 0.95,
            "teacher_data_incomplete": teacher_ratio < 0.95
        }
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--xml", required=True, help="Purdue/ITC XML source file")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    data = parse_purdue_xml(Path(args.xml))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    write_csv(out / "cleaned_courses.csv", data["courses"], REQUIRED_COURSE_COLS)
    write_csv(out / "cleaned_rooms.csv", data["rooms"], REQUIRED_ROOM_COLS)
    write_csv(out / "cleaned_teachers.csv", data["teachers"], REQUIRED_TEACHER_COLS)

    report = diagnostics(data["courses"], data["rooms"])
    with (out / "diagnostic_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
