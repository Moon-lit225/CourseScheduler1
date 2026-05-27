"""
大学课程排课系统 - 成员 C 核心实现

在成员 A（数据）与成员 B（贪心/遗传 + 目标函数）基础上：
- 决策变量：每门课的教室（时间槽来自 ITC XML 已给定的首选时段）
- 目标：最小化教室时间冲突，提高教室利用率，尽量多排课
- 约束：教室容量、同一教室时段不重叠（含跨天 bitmask 重叠检测）

用法：
    python scheduler.py              # 默认贪心
    python scheduler.py --algorithm ga
    python scheduler.py --algorithm both
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import (
    ASSIGNMENT_BONUS,
    CONFLICT_PENALTY,
    COURSES_CSV,
    GA_ELITE_COUNT,
    GA_GENERATIONS,
    GA_MUTATION_RATE,
    GA_POPULATION,
    ROOMS_CSV,
    SCHEDULE_CSV,
    STATS_JSON,
    UTILIZATION_WEIGHT,
)

DAY_NAMES = {
    "1000000": "周一",
    "0100000": "周二",
    "0010000": "周三",
    "0001000": "周四",
    "0000100": "周五",
    "0000010": "周六",
    "0000001": "周日",
}


def parse_day_mask(day: str) -> List[int]:
    """将 ITC days 字符串转为星期索引列表（0=周一）"""
    day = (day or "").ljust(7, "0")[:7]
    return [i for i, ch in enumerate(day) if ch == "1"]


def day_mask_label(day: str) -> str:
    indices = parse_day_mask(day)
    if not indices:
        return day or "未指定"
    labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return "+".join(labels[i] for i in indices)


def days_overlap(day_a: str, day_b: str) -> bool:
    a = (day_a or "").ljust(7, "0")[:7]
    b = (day_b or "").ljust(7, "0")[:7]
    return any(x == "1" and y == "1" for x, y in zip(a, b))


def time_overlap(start_a: int, len_a: int, start_b: int, len_b: int) -> bool:
    end_a, end_b = start_a + len_a, start_b + len_b
    return not (end_a <= start_b or end_b <= start_a)


@dataclass
class Course:
    course_id: str
    student_limit: int
    day: str
    start: int
    length: int
    room_id: Optional[str] = None

    @property
    def end(self) -> int:
        return self.start + self.length


@dataclass
class Room:
    room_id: str
    capacity: int


@dataclass
class ScheduledSlot:
    course_id: str
    day: str
    start: int
    length: int
    student_limit: int


class CourseScheduler:
    """教室分配排课器：时间在 courses.csv 中由成员 A 从 XML 导出。"""

    def __init__(self, seed: int = 42):
        self.courses: List[Course] = []
        self.rooms: List[Room] = []
        self.schedule: Dict[str, List[ScheduledSlot]] = {}
        random.seed(seed)

    # ---------- 数据加载 ----------
    def load_courses(self, path: Path) -> None:
        with path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                limit_raw = (row.get("student_limit") or "").strip()
                start_raw = (row.get("start") or "").strip()
                length_raw = (row.get("length") or "").strip()
                self.courses.append(
                    Course(
                        course_id=row["course_id"],
                        student_limit=int(limit_raw) if limit_raw else 0,
                        day=row.get("day") or "",
                        start=int(start_raw) if start_raw else 0,
                        length=int(length_raw) if length_raw else 0,
                    )
                )

    def load_rooms(self, path: Path) -> None:
        with path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                self.rooms.append(
                    Room(
                        room_id=row["room_id"],
                        capacity=int(row["capacity"]),
                    )
                )

    # ---------- 冲突与适应度（成员 B 目标函数） ----------
    @staticmethod
    def slot_conflict(a: ScheduledSlot, b: ScheduledSlot) -> bool:
        if a.course_id == b.course_id:
            return False
        if not days_overlap(a.day, b.day):
            return False
        return time_overlap(a.start, a.length, b.start, b.length)

    def _room_has_conflict(self, room_id: str, course: Course) -> bool:
        probe = ScheduledSlot(
            course_id=course.course_id,
            day=course.day,
            start=course.start,
            length=course.length,
            student_limit=course.student_limit,
        )
        for existing in self.schedule.get(room_id, []):
            if self.slot_conflict(probe, existing):
                return True
        return False

    def _feasible_rooms(self, course: Course) -> List[Room]:
        result = []
        for room in self.rooms:
            if room.capacity < course.student_limit:
                continue
            if self._room_has_conflict(room.room_id, course):
                continue
            result.append(room)
        return result

    def _assign(self, course: Course, room: Room) -> None:
        course.room_id = room.room_id
        self.schedule.setdefault(room.room_id, []).append(
            ScheduledSlot(
                course_id=course.course_id,
                day=course.day,
                start=course.start,
                length=course.length,
                student_limit=course.student_limit,
            )
        )

    def _clear_assignments(self) -> None:
        self.schedule.clear()
        for c in self.courses:
            c.room_id = None

    def count_conflicts(self) -> int:
        conflicts = 0
        for slots in self.schedule.values():
            for i in range(len(slots)):
                for j in range(i + 1, len(slots)):
                    if self.slot_conflict(slots[i], slots[j]):
                        conflicts += 1
        return conflicts

    def calculate_fitness(self) -> float:
        """
        成员 B 目标函数（越大越好）：
        fitness = -冲突数 * CONFLICT_PENALTY
                  + 教室利用率 * UTILIZATION_WEIGHT
                  + 已排课程数 * ASSIGNMENT_BONUS
        """
        conflicts = self.count_conflicts()
        assigned = [c for c in self.courses if c.room_id]
        used_minutes = sum(s.length for slots in self.schedule.values() for s in slots)
        # 10 间教室 × 工作日 5 天 × 每天约 14 小时（840 分钟）的粗算分母
        capacity_denominator = max(len(self.rooms) * 5 * 840, 1)
        utilization = used_minutes / capacity_denominator

        return (
            -conflicts * CONFLICT_PENALTY
            + utilization * UTILIZATION_WEIGHT
            + len(assigned) * ASSIGNMENT_BONUS
        )

    # ---------- 贪心启发式（成员 B 建议） ----------
    def greedy_schedule(self) -> float:
        self._clear_assignments()
        ordered = sorted(
            self.courses,
            key=lambda c: (-c.student_limit, -c.length, c.start),
        )
        for course in ordered:
            candidates = self._feasible_rooms(course)
            if not candidates:
                continue
            # 选容量最小且够用的教室 → 提高利用率
            best = min(candidates, key=lambda r: r.capacity)
            self._assign(course, best)
        return self.calculate_fitness()

    # ---------- 遗传算法（成员 B 备选方案） ----------
    def _encode(self) -> List[int]:
        """染色体：每门课对应 room 下标，-1 表示不分配"""
        return [-1] * len(self.courses)

    def _decode(self, chromosome: List[int]) -> None:
        self._clear_assignments()
        for gene, course in zip(chromosome, self.courses):
            if gene < 0 or gene >= len(self.rooms):
                continue
            room = self.rooms[gene]
            if room.capacity < course.student_limit:
                continue
            if self._room_has_conflict(room.room_id, course):
                continue
            self._assign(course, room)

    def _random_chromosome(self) -> List[int]:
        chrom = []
        for course in self.courses:
            feasible = list(range(len(self.rooms)))
            random.shuffle(feasible)
            picked = -1
            for idx in feasible:
                room = self.rooms[idx]
                if room.capacity < course.student_limit:
                    continue
                if self._room_has_conflict(room.room_id, course):
                    continue
                picked = idx
                break
            chrom.append(picked)
            if picked >= 0:
                self._assign(course, self.rooms[picked])
        self._clear_assignments()
        return chrom

    def _mutate(self, chromosome: List[int]) -> List[int]:
        child = chromosome[:]
        if not self.courses:
            return child
        idx = random.randrange(len(self.courses))
        course = self.courses[idx]
        if random.random() < 0.5:
            child[idx] = -1
        else:
            options = [-1] + list(range(len(self.rooms)))
            random.shuffle(options)
            for gene in options:
                child[idx] = gene
                self._decode(child)
                if gene < 0 or not self._room_has_conflict(self.rooms[gene].room_id, course):
                    break
            self._clear_assignments()
        return child

    def genetic_schedule(
        self,
        population_size: int = GA_POPULATION,
        generations: int = GA_GENERATIONS,
        mutation_rate: float = GA_MUTATION_RATE,
        elite_count: int = GA_ELITE_COUNT,
    ) -> float:
        population = [self._random_chromosome() for _ in range(population_size)]

        def evaluate(chrom: List[int]) -> float:
            self._decode(chrom)
            return self.calculate_fitness()

        best_chrom, best_fit = None, float("-inf")

        for _ in range(generations):
            scored = [(evaluate(ch), ch) for ch in population]
            scored.sort(key=lambda x: x[0], reverse=True)
            if scored[0][0] > best_fit:
                best_fit, best_chrom = scored[0]

            elites = [ch for _, ch in scored[:elite_count]]
            new_pop = elites[:]
            while len(new_pop) < population_size:
                p1, p2 = random.choice(elites), random.choice(scored[: population_size // 2])[1]
                point = random.randrange(1, len(self.courses)) if len(self.courses) > 1 else 1
                child = p1[:point] + p2[point:]
                if random.random() < mutation_rate:
                    child = self._mutate(child)
                new_pop.append(child)
            population = new_pop

        if best_chrom is not None:
            self._decode(best_chrom)
        return self.calculate_fitness()

    # ---------- 输出 ----------
    def save_schedule(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        room_cap = {r.room_id: r.capacity for r in self.rooms}
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "course_id",
                    "student_limit",
                    "day",
                    "day_name",
                    "start_time",
                    "end_time",
                    "length",
                    "room",
                    "room_capacity",
                    "status",
                ]
            )
            for course in sorted(self.courses, key=lambda c: c.course_id):
                if course.room_id:
                    cap = room_cap.get(course.room_id, "")
                    status = "assigned"
                    room_name = course.room_id
                else:
                    cap, status, room_name = "", "unassigned", "Unassigned"

                sh, sm = divmod(course.start, 60)
                eh, em = divmod(course.end, 60)
                writer.writerow(
                    [
                        course.course_id,
                        course.student_limit,
                        course.day,
                        day_mask_label(course.day),
                        f"{sh:02d}:{sm:02d}",
                        f"{eh:02d}:{em:02d}",
                        course.length,
                        room_name,
                        cap,
                        status,
                    ]
                )

    def save_stats(self, path: Path, algorithm: str, fitness: float) -> None:
        assigned = sum(1 for c in self.courses if c.room_id)
        stats = {
            "algorithm": algorithm,
            "fitness": round(fitness, 4),
            "total_courses": len(self.courses),
            "assigned_courses": assigned,
            "unassigned_courses": len(self.courses) - assigned,
            "conflicts": self.count_conflicts(),
            "rooms_used": len(self.schedule),
            "assignment_rate": round(assigned / max(len(self.courses), 1) * 100, 2),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
        return stats

    def print_statistics(self, algorithm: str, fitness: float) -> None:
        assigned = sum(1 for c in self.courses if c.room_id)
        used_rooms = len(self.schedule)
        used_minutes = sum(s.length for slots in self.schedule.values() for s in slots)
        denom = max(len(self.rooms) * 5 * 840, 1)
        utilization = used_minutes / denom * 100

        print("\n=== 排课统计 ===")
        print(f"算法: {algorithm}")
        print(f"适应度: {fitness:.2f}")
        print(f"总课程数: {len(self.courses)}")
        print(f"已成功排课: {assigned} ({assigned / max(len(self.courses), 1) * 100:.1f}%)")
        print(f"未分配课程: {len(self.courses) - assigned}")
        print(f"教室时间冲突: {self.count_conflicts()}")
        print(f"使用教室数: {used_rooms}/{len(self.rooms)}")
        print(f"教室利用率(估算): {utilization:.2f}%")


def run(algorithm: str) -> None:
    scheduler = CourseScheduler()
    scheduler.load_courses(COURSES_CSV)
    scheduler.load_rooms(ROOMS_CSV)

    print(f"加载课程: {len(scheduler.courses)} 门")
    print(f"加载教室: {len(scheduler.rooms)} 间")

    results: List[Tuple[str, float]] = []

    if algorithm in ("greedy", "both"):
        fit = scheduler.greedy_schedule()
        scheduler.print_statistics("贪心启发式", fit)
        results.append(("greedy", fit))
        if algorithm == "greedy":
            scheduler.save_schedule(SCHEDULE_CSV)
            scheduler.save_stats(STATS_JSON, "greedy", fit)

    if algorithm in ("ga", "both"):
        fit_ga = scheduler.genetic_schedule()
        scheduler.print_statistics("遗传算法", fit_ga)
        results.append(("ga", fit_ga))
        scheduler.save_schedule(SCHEDULE_CSV)
        scheduler.save_stats(STATS_JSON, "ga", fit_ga)

    if algorithm == "both":
        best = max(results, key=lambda x: x[1])
        print(f"\n最终采用算法: {best[0]} (适应度 {best[1]:.2f})")
        if best[0] == "greedy":
            scheduler.greedy_schedule()
        else:
            scheduler.genetic_schedule()
        scheduler.save_schedule(SCHEDULE_CSV)
        scheduler.save_stats(STATS_JSON, best[0], best[1])


def main() -> None:
    parser = argparse.ArgumentParser(description="大学课程排课 - 成员 C")
    parser.add_argument(
        "--algorithm",
        choices=["greedy", "ga", "both"],
        default="greedy",
        help="greedy=贪心, ga=遗传算法, both=两种都跑并选更优",
    )
    args = parser.parse_args()
    run(args.algorithm)


if __name__ == "__main__":
    main()
