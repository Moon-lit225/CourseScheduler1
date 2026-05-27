import xml.etree.ElementTree as ET
import csv

print("开始解析课程数据...\n")

tree = ET.parse('../data/pu-spr07-cs.xml')
root = tree.getroot()

classes = root.find('classes')

# 创建 CSV 文件
with open('../output/courses.csv', 'w', newline='', encoding='utf-8') as file:

    writer = csv.writer(file)

    # CSV 表头
    writer.writerow([
        'course_id',
        'student_limit',
        'day',
        'start',
        'length'
    ])

    # 遍历课程
    for c in classes:

        course_id = c.get('id')
        student_limit = c.get('classLimit')

        # 找第一种可选时间
        first_time = c.find('time')

        if first_time is not None:

            day = first_time.get('days')
            start = first_time.get('start')
            length = first_time.get('length')

        else:

            day = ''
            start = ''
            length = ''

        writer.writerow([
            course_id,
            student_limit,
            day,
            start,
            length
        ])

print("courses.csv 导出成功！")
print("程序结束！")