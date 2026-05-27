# CourseScheduler1

大学排课系统数据清洗工具（XML 解析优先，且房间仅使用 XML）。

## 关键说明

你说得对：为了避免混淆，**房间数据统一只用 XML**，不再合并自定义房间。

- 课程、教师、教室都从同一份 XML 解析
- 清洗后输出标准 CSV + 诊断报告
- 只保留“房间规模建议”用于你后续人工扩容决策，不直接混入自定义房间

## 运行方法

```bash
python tools/data_cleaning_pipeline.py \
  --xml path/to/your_data.xml \
  --out data/cleaned
```

## 输出文件

- `cleaned_courses.csv`
- `cleaned_rooms.csv`（仅来自 XML）
- `cleaned_teachers.csv`
- `diagnostic_report.json`

## 房间建议字段说明

`diagnostic_report.json` 中：
- `room_recommendation.suggested_room_count`：建议教室数量
- `room_recommendation.suggested_room_capacity`：建议主力容量

估算逻辑：
- 目标利用率默认 0.75
- 每间教室默认每周 50 时段
- `建议教室数 ≈ ceil(总周学时 / (目标利用率 × 每间教室周时段))`
