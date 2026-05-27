"""路径与算法参数（成员 B 目标函数权重可在此调整）"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

COURSES_CSV = OUTPUT_DIR / "courses.csv"
ROOMS_CSV = DATA_DIR / "rooms.csv"
SCHEDULE_CSV = OUTPUT_DIR / "schedule_result.csv"
STATS_JSON = OUTPUT_DIR / "schedule_stats.json"

# 成员 B 定义的目标函数权重
CONFLICT_PENALTY = 1000.0
UTILIZATION_WEIGHT = 100.0
ASSIGNMENT_BONUS = 10.0

# 遗传算法默认参数（成员 E 可继续调参）
GA_POPULATION = 80
GA_GENERATIONS = 120
GA_MUTATION_RATE = 0.15
GA_ELITE_COUNT = 4
