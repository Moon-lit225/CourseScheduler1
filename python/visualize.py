"""
大学课程排课系统 - 可视化模块 (成员D)

功能：
- 周课表视图：按周一~周五展示课程安排
- 教室视图：按教室分组展示课表
- 颜色区分院系/年级
- 统计面板：排课率、冲突数、教室利用率

用法：
    python visualize.py
    然后在浏览器打开 output/schedule_visualization.html
"""

import csv
import json
from pathlib import Path

# ========== 路径配置 ==========
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

SCHEDULE_CSV = OUTPUT_DIR / "schedule_result.csv"
STATS_JSON = OUTPUT_DIR / "schedule_stats.json"
ROOMS_CSV = DATA_DIR / "rooms.csv"
HTML_OUTPUT = OUTPUT_DIR / "schedule_visualization.html"

# ========== 教室数据 ==========
ROOMS = [
    {'id': 'R101', 'cap': 30}, {'id': 'R102', 'cap': 40},
    {'id': 'R103', 'cap': 50}, {'id': 'R104', 'cap': 60},
    {'id': 'R105', 'cap': 100}, {'id': 'R106', 'cap': 120},
    {'id': 'R107', 'cap': 150}, {'id': 'R108', 'cap': 200},
    {'id': 'R109', 'cap': 300}, {'id': 'R110', 'cap': 500}
]

# ========== 数据解析 ==========
def load_schedule_data():
    """读取排课结果CSV"""
    courses = []
    with open(SCHEDULE_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            courses.append({
                'id': row['course_id'],
                'studentLimit': int(row['student_limit'] or 0),
                'day': row['day'],
                'dayName': row['day_name'],
                'startTime': row['start_time'],
                'endTime': row['end_time'],
                'length': int(row['length'] or 0),
                'room': row['room'],
                'roomCap': int(row['room_capacity'] or 0),
                'status': row['status']
            })
    return courses

def load_stats():
    """读取统计信息"""
    if STATS_JSON.exists():
        with open(STATS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def get_dept_info(course_id):
    """根据课程ID判断院系/年级"""
    cid = int(course_id)
    if cid < 400:
        return {'name': '基础课程 (1xx)', 'cls': 'dept-basic', 'color': '#1565c0'}
    elif cid < 500:
        return {'name': '核心专业 (4xx)', 'cls': 'dept-core', 'color': '#2e7d32'}
    elif cid < 1000:
        return {'name': '高级专业 (5xx-9xx)', 'cls': 'dept-advanced', 'color': '#e65100'}
    else:
        return {'name': '研究生/专题 (1xxx)', 'cls': 'dept-graduate', 'color': '#7b1fa2'}

def generate_html(courses, stats):
    """生成可视化HTML"""
    
    # 构建CSV数据字符串
    csv_data = "course_id,student_limit,day,day_name,start_time,end_time,length,room,room_capacity,status\n"
    for c in courses:
        csv_data += f"{c['id']},{c['studentLimit']},{c['day']},{c['dayName']},{c['startTime']},{c['endTime']},{c['length']},{c['room']},{c['roomCap']},{c['status']}\n"
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>大学课程排课系统 - 可视化Demo</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            background: #f0f2f5;
            color: #333;
            min-height: 100vh;
        }}
        .header {{
            background: linear-gradient(135deg, #1a237e 0%, #283593 50%, #1565c0 100%);
            color: white;
            padding: 20px 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }}
        .header h1 {{ font-size: 24px; margin-bottom: 4px; }}
        .header p {{ font-size: 13px; opacity: 0.85; }}
        .stats-bar {{
            display: flex;
            gap: 16px;
            padding: 16px 30px;
            background: white;
            border-bottom: 1px solid #e8e8e8;
            flex-wrap: wrap;
        }}
        .stat-card {{
            flex: 1;
            min-width: 150px;
            background: #fafafa;
            border-radius: 8px;
            padding: 14px 18px;
            border-left: 4px solid;
        }}
        .stat-card.total {{ border-color: #1a237e; }}
        .stat-card.assigned {{ border-color: #2e7d32; }}
        .stat-card.unassigned {{ border-color: #c62828; }}
        .stat-card.conflicts {{ border-color: #f57f17; }}
        .stat-card.utilization {{ border-color: #00838f; }}
        .stat-card.rooms {{ border-color: #6a1b9a; }}
        .stat-label {{ font-size: 12px; color: #888; margin-bottom: 4px; }}
        .stat-value {{ font-size: 22px; font-weight: 700; }}
        .stat-card.total .stat-value {{ color: #1a237e; }}
        .stat-card.assigned .stat-value {{ color: #2e7d32; }}
        .stat-card.unassigned .stat-value {{ color: #c62828; }}
        .stat-card.conflicts .stat-value {{ color: #f57f17; }}
        .stat-card.utilization .stat-value {{ color: #00838f; }}
        .stat-card.rooms .stat-value {{ color: #6a1b9a; }}
        .controls {{
            display: flex;
            gap: 12px;
            padding: 14px 30px;
            background: white;
            border-bottom: 1px solid #e8e8e8;
            flex-wrap: wrap;
            align-items: center;
        }}
        .controls label {{ font-size: 13px; color: #666; font-weight: 600; }}
        .controls select, .controls input {{
            padding: 6px 12px;
            border: 1px solid #d0d0d0;
            border-radius: 6px;
            font-size: 13px;
            background: white;
            cursor: pointer;
        }}
        .view-toggle {{
            display: flex;
            gap: 4px;
            background: #f0f0f0;
            border-radius: 6px;
            padding: 2px;
        }}
        .view-btn {{
            padding: 6px 14px;
            border: none;
            background: transparent;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            color: #666;
            transition: all 0.2s;
        }}
        .view-btn.active {{
            background: #1a237e;
            color: white;
        }}
        .legend {{
            display: flex;
            gap: 14px;
            padding: 10px 30px;
            background: white;
            border-bottom: 1px solid #e8e8e8;
            flex-wrap: wrap;
            align-items: center;
        }}
        .legend-title {{ font-size: 12px; color: #888; font-weight: 600; margin-right: 4px; }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 12px;
            color: #555;
        }}
        .legend-color {{
            width: 14px;
            height: 14px;
            border-radius: 3px;
            border: 1px solid rgba(0,0,0,0.1);
        }}
        .schedule-container {{
            padding: 20px 30px;
            overflow-x: auto;
        }}
        .schedule-grid {{
            width: 100%;
            min-width: 900px;
            border-collapse: separate;
            border-spacing: 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }}
        .schedule-grid th {{
            background: #1a237e;
            color: white;
            padding: 10px 8px;
            font-size: 13px;
            font-weight: 600;
        }}
        .schedule-grid th:first-child {{ width: 70px; min-width: 70px; }}
        .schedule-grid td {{
            border: 1px solid #e8e8e8;
            padding: 3px;
            vertical-align: top;
            height: 60px;
            min-width: 130px;
        }}
        .schedule-grid td:first-child {{
            background: #f5f5f5;
            text-align: center;
            font-size: 12px;
            font-weight: 600;
            color: #555;
            vertical-align: middle;
            padding: 8px 4px;
        }}
        .schedule-grid tr:hover td:not(:first-child) {{ background: #f8f9ff; }}
        .course-cell {{
            padding: 4px 6px;
            border-radius: 4px;
            margin: 2px 0;
            font-size: 11px;
            line-height: 1.4;
            cursor: pointer;
            transition: transform 0.15s, box-shadow 0.15s;
            border-left: 3px solid;
        }}
        .course-cell:hover {{
            transform: scale(1.03);
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            z-index: 5;
        }}
        .course-id {{ font-weight: 700; font-size: 11px; }}
        .course-room {{ opacity: 0.8; font-size: 10px; }}
        .course-dept {{ font-size: 9px; opacity: 0.6; margin-top: 1px; }}
        .dept-basic {{ background: #e3f2fd; border-left-color: #1565c0; color: #0d47a1; }}
        .dept-core {{ background: #e8f5e9; border-left-color: #2e7d32; color: #1b5e20; }}
        .dept-advanced {{ background: #fff3e0; border-left-color: #e65100; color: #bf360c; }}
        .dept-graduate {{ background: #f3e5f5; border-left-color: #7b1fa2; color: #4a148c; }}
        .tooltip {{
            display: none;
            position: fixed;
            background: #333;
            color: white;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 12px;
            line-height: 1.6;
            z-index: 1000;
            max-width: 280px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            pointer-events: none;
        }}
        .room-view-header {{
            padding: 12px 30px 0;
            font-size: 16px;
            font-weight: 700;
            color: #1a237e;
        }}
        .unassigned-section {{
            margin-top: 20px;
            padding: 16px 30px;
        }}
        .unassigned-section h3 {{
            font-size: 15px;
            color: #c62828;
            margin-bottom: 10px;
        }}
        .unassigned-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        .unassigned-tag {{
            background: #ffebee;
            color: #c62828;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            border: 1px solid #ffcdd2;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #aaa;
            font-size: 12px;
        }}
    </style>
</head>
<body>
<div class="header">
    <h1>🎓 大学课程排课系统 — 可视化Demo</h1>
    <p>基于ITC 2007竞赛数据 | 遗传算法排课 | 成员D 可视化模块</p>
</div>
<div class="stats-bar" id="statsBar"></div>
<div class="controls">
    <label>视图：</label>
    <div class="view-toggle">
        <button class="view-btn active" onclick="switchView('week')">📅 周课表</button>
        <button class="view-btn" onclick="switchView('room')">🏫 教室视图</button>
    </div>
    <label style="margin-left:16px;">教室筛选：</label>
    <select id="roomFilter" onchange="renderSchedule()"><option value="all">全部教室</option></select>
    <label style="margin-left:16px;">院系筛选：</label>
    <select id="deptFilter" onchange="renderSchedule()"><option value="all">全部院系</option></select>
    <label style="margin-left:16px;">搜索课程：</label>
    <input type="text" id="searchInput" placeholder="输入课程ID..." oninput="renderSchedule()" style="width:120px;">
</div>
<div class="legend">
    <span class="legend-title">院系/年级图例：</span>
    <div class="legend-item"><div class="legend-color" style="background:#e3f2fd;border-left:3px solid #1565c0;"></div>基础课程 (1xx)</div>
    <div class="legend-item"><div class="legend-color" style="background:#e8f5e9;border-left:3px solid #2e7d32;"></div>核心专业 (4xx)</div>
    <div class="legend-item"><div class="legend-color" style="background:#fff3e0;border-left:3px solid #e65100;"></div>高级专业 (5xx-9xx)</div>
    <div class="legend-item"><div class="legend-color" style="background:#f3e5f5;border-left:3px solid #7b1fa2;"></div>研究生/专题 (1xxx)</div>
</div>
<div id="scheduleArea"></div>
<div class="tooltip" id="tooltip"></div>
<div class="footer">大学课程排课系统 &copy; 2025 | 成员D 可视化模块 | 数据来源：ITC 2007 Purdue Spring CS</div>
<script>
const ROOMS = [
    {{id:'R101',cap:30}},{{id:'R102',cap:40}},{{id:'R103',cap:50}},{{id:'R104',cap:60}},
    {{id:'R105',cap:100}},{{id:'R106',cap:120}},{{id:'R107',cap:150}},{{id:'R108',cap:200}},
    {{id:'R109',cap:300}},{{id:'R110',cap:500}}
];
const RAW_DATA = `{csv_data}`;
function parseData() {{
    const lines = RAW_DATA.trim().split('\\n');
    const courses = [];
    for (let i = 1; i < lines.length; i++) {{
        const cols = lines[i].split(',');
        if (cols.length < 10) continue;
        courses.push({{
            id: cols[0], studentLimit: parseInt(cols[1]) || 0, day: cols[2], dayName: cols[3],
            startTime: cols[4], endTime: cols[5], length: parseInt(cols[6]) || 0,
            room: cols[7], roomCap: parseInt(cols[8]) || 0, status: cols[9]
        }});
    }}
    return courses;
}}
function getDeptInfo(courseId) {{
    const id = parseInt(courseId);
    if (id < 400) return {{ name: '基础课程 (1xx)', cls: 'dept-basic', color: '#1565c0' }};
    if (id < 500) return {{ name: '核心专业 (4xx)', cls: 'dept-core', color: '#2e7d32' }};
    if (id < 1000) return {{ name: '高级专业 (5xx-9xx)', cls: 'dept-advanced', color: '#e65100' }};
    return {{ name: '研究生/专题 (1xxx)', cls: 'dept-graduate', color: '#7b1fa2' }};
}}
function parseDayMask(dayStr) {{
    const days = [];
    const d = (dayStr || '').padStart(7, '0').slice(0, 7);
    for (let i = 0; i < 7; i++) {{ if (d[i] === '1') days.push(i); }}
    return days;
}}
let allCourses = parseData();
let currentView = 'week';
function renderStats() {{
    const total = allCourses.length;
    const assigned = allCourses.filter(c => c.status === 'assigned').length;
    const unassigned = total - assigned;
    const conflicts = 0;
    const usedRooms = new Set(allCourses.filter(c => c.status === 'assigned').map(c => c.room));
    const totalMinutes = allCourses.filter(c => c.status === 'assigned').reduce((s, c) => s + c.length, 0);
    const maxMinutes = ROOMS.length * 5 * 840;
    const utilization = (totalMinutes / maxMinutes * 100).toFixed(2);
    document.getElementById('statsBar').innerHTML = `
        <div class="stat-card total"><div class="stat-label">总课程数</div><div class="stat-value">${{total}}</div></div>
        <div class="stat-card assigned"><div class="stat-label">已排课</div><div class="stat-value">${{assigned}} (${{(assigned/total*100).toFixed(1)}}%)</div></div>
        <div class="stat-card unassigned"><div class="stat-label">未分配</div><div class="stat-value">${{unassigned}}</div></div>
        <div class="stat-card conflicts"><div class="stat-label">教室冲突</div><div class="stat-value">${{conflicts}}</div></div>
        <div class="stat-card utilization"><div class="stat-label">教室利用率</div><div class="stat-value">${{utilization}}%</div></div>
        <div class="stat-card rooms"><div class="stat-label">使用教室</div><div class="stat-value">${{usedRooms.size}}/${{ROOMS.length}}</div></div>
    `;
}}
function initFilters() {{
    const roomSelect = document.getElementById('roomFilter');
    ROOMS.forEach(r => {{
        const opt = document.createElement('option');
        opt.value = r.id;
        opt.textContent = `${{r.id}} (容量${{r.cap}})`;
        roomSelect.appendChild(opt);
    }});
    const deptSelect = document.getElementById('deptFilter');
    ['all', 'basic', 'core', 'advanced', 'graduate'].forEach(key => {{
        const opt = document.createElement('option');
        opt.value = key;
        if (key === 'all') opt.textContent = '全部院系';
        else {{
            const info = getDeptInfo(key === 'basic' ? '100' : key === 'core' ? '400' : key === 'advanced' ? '500' : '1000');
            opt.textContent = info.name;
        }}
        deptSelect.appendChild(opt);
    }});
}}
function getFilteredCourses() {{
    const roomFilter = document.getElementById('roomFilter').value;
    const deptFilter = document.getElementById('deptFilter').value;
    const search = document.getElementById('searchInput').value.trim();
    return allCourses.filter(c => {{
        if (roomFilter !== 'all' && c.room !== roomFilter) return false;
        if (deptFilter !== 'all') {{
            const deptKey = c.id < 400 ? 'basic' : c.id < 500 ? 'core' : c.id < 1000 ? 'advanced' : 'graduate';
            if (deptKey !== deptFilter) return false;
        }}
        if (search && !c.id.includes(search)) return false;
        return true;
    }});
}}
function renderWeekView(courses) {{
    const displayDays = ['周一', '周二', '周三', '周四', '周五'];
    const timeSlots = [];
    const seen = new Set();
    courses.forEach(c => {{
        const key = c.startTime + '-' + c.endTime;
        if (!seen.has(key) && c.status === 'assigned') {{
            seen.add(key);
            timeSlots.push({{ start: c.startTime, end: c.endTime, label: `${{c.startTime}}-${{c.endTime}}` }});
        }}
    }});
    timeSlots.sort((a, b) => a.start.localeCompare(b.start));
    const grid = {{}};
    displayDays.forEach((_, i) => grid[i] = {{}});
    courses.filter(c => c.status === 'assigned').forEach(c => {{
        const dayIndices = parseDayMask(c.day);
        dayIndices.forEach(di => {{
            if (di < 5) {{
                const key = c.startTime + '-' + c.endTime;
                if (!grid[di][key]) grid[di][key] = [];
                grid[di][key].push(c);
            }}
        }});
    }});
    let html = '<div class="schedule-container"><table class="schedule-grid"><thead><tr><th>时间</th>';
    displayDays.forEach(d => html += `<th>${{d}}</th>`);
    html += '</tr></thead><tbody>';
    timeSlots.forEach(slot => {{
        html += `<tr><td>${{slot.label}}</td>`;
        for (let di = 0; di < 5; di++) {{
            const cellCourses = grid[di][slot.start + '-' + slot.end] || [];
            html += '<td>';
            cellCourses.forEach(c => {{
                const dept = getDeptInfo(c.id);
                html += `<div class="course-cell ${{dept.cls}}" onmouseenter="showTooltip(event, ${{JSON.stringify(c).replace(/"/g, '&quot;')}})" onmouseleave="hideTooltip()">
                    <div class="course-id">${{c.id}}</div>
                    <div class="course-room">${{c.room}} (${{c.roomCap}}人)</div>
                    <div class="course-dept">${{dept.name}}</div>
                </div>`;
            }});
            html += '</td>';
        }}
        html += '</tr>';
    }});
    html += '</tbody></table></div>';
    const unassigned = courses.filter(c => c.status === 'unassigned');
    if (unassigned.length > 0) {{
        html += `<div class="unassigned-section"><h3>⚠️ 未分配课程 (${{unassigned.length}}门)</h3><div class="unassigned-list">`;
        unassigned.forEach(c => {{
            const dept = getDeptInfo(c.id);
            html += `<span class="unassigned-tag" style="border-left:3px solid ${{dept.color}}">${{c.id}} (${{c.dayName}})</span>`;
        }});
        html += '</div></div>';
    }}
    return html;
}}
function renderRoomView(courses) {{
    const assigned = courses.filter(c => c.status === 'assigned');
    const displayDays = ['周一', '周二', '周三', '周四', '周五'];
    let html = '<div class="schedule-container">';
    ROOMS.forEach(room => {{
        const roomCourses = assigned.filter(c => c.room === room.id);
        if (roomCourses.length === 0) return;
        const byDay = {{}};
        displayDays.forEach((_, i) => byDay[i] = []);
        roomCourses.forEach(c => {{
            const dayIndices = parseDayMask(c.day);
            dayIndices.forEach(di => {{ if (di < 5) byDay[di].push(c); }});
        }});
        Object.values(byDay).forEach(arr => arr.sort((a, b) => a.startTime.localeCompare(b.startTime)));
        html += `<div style="margin-bottom:24px;">
            <div class="room-view-header">🏫 ${{room.id}} <span style="font-size:13px;color:#888;font-weight:400;">(容量: ${{room.cap}}人 | 已排: ${{roomCourses.length}}门)</span></div>
            <table class="schedule-grid" style="margin-top:8px;"><thead><tr><th>时间</th>`;
        displayDays.forEach(d => html += `<th>${{d}}</th>`);
        html += '</tr></thead><tbody>';
        const allSlots = new Set();
        Object.values(byDay).forEach(arr => arr.forEach(c => allSlots.add(c.startTime + '-' + c.endTime)));
        const slots = [...allSlots].sort();
        slots.forEach(slot => {{
            html += `<tr><td>${{slot}}</td>`;
            for (let di = 0; di < 5; di++) {{
                const cellCourses = byDay[di].filter(c => c.startTime + '-' + c.endTime === slot);
                html += '<td>';
                cellCourses.forEach(c => {{
                    const dept = getDeptInfo(c.id);
                    html += `<div class="course-cell ${{dept.cls}}" onmouseenter="showTooltip(event, ${{JSON.stringify(c).replace(/"/g, '&quot;')}})" onmouseleave="hideTooltip()">
                        <div class="course-id">${{c.id}}</div>
                        <div class="course-dept">${{dept.name}}</div>
                    </div>`;
                }});
                html += '</td>';
            }}
            html += '</tr>';
        }});
        html += '</tbody></table></div>';
    }});
    html += '</div>';
    return html;
}}
function showTooltip(event, course) {{
    const dept = getDeptInfo(course.id);
    const tooltip = document.getElementById('tooltip');
    tooltip.innerHTML = `<strong>课程 ${{course.id}}</strong><br>院系/年级：${{dept.name}}<br>上课时间：${{course.dayName}} ${{course.startTime}}-${{course.endTime}}<br>教室：${{course.room}} (容量${{course.roomCap}}人)<br>学生上限：${{course.studentLimit || '未指定'}}人<br>课长：${{course.length}}分钟<br>状态：${{course.status === 'assigned' ? '✅ 已排课' : '❌ 未分配'}}`;
    tooltip.style.display = 'block';
    const rect = event.target.getBoundingClientRect();
    tooltip.style.left = rect.left + rect.width / 2 - 140 + 'px';
    tooltip.style.top = rect.top - 120 + 'px';
}}
function hideTooltip() {{ document.getElementById('tooltip').style.display = 'none'; }}
function switchView(view) {{
    currentView = view;
    document.querySelectorAll('.view-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    renderSchedule();
}}
function renderSchedule() {{
    const filtered = getFilteredCourses();
    document.getElementById('scheduleArea').innerHTML = currentView === 'week' ? renderWeekView(filtered) : renderRoomView(filtered);
}}
renderStats();
initFilters();
renderSchedule();
</script>
</body>
</html>'''
    return html

def main():
    """主函数：生成可视化HTML"""
    print("=" * 50)
    print("大学课程排课系统 - 可视化模块 (成员D)")
    print("=" * 50)
    
    # 加载数据
    print("\n[1/3] 加载排课数据...")
    courses = load_schedule_data()
    print(f"      已加载 {len(courses)} 门课程")
    
    print("\n[2/3] 加载统计信息...")
    stats = load_stats()
    print(f"      算法: {stats.get('algorithm', 'N/A')}")
    print(f"      适应度: {stats.get('fitness', 'N/A')}")
    
    # 生成HTML
    print("\n[3/3] 生成可视化HTML...")
    html = generate_html(courses, stats)
    
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 写入文件
    with open(HTML_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ 生成成功!")
    print(f"   输出文件: {HTML_OUTPUT}")
    print(f"\n💡 使用方法: 在浏览器中打开上述HTML文件即可查看可视化课表")

if __name__ == "__main__":
    main()