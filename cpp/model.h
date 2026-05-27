#ifndef MODEL_H
#define MODEL_H

#include <string>

using namespace std;

// 课程
struct Course {

    string course_id;

    int student_limit;

    string day;

    int start;

    int length;

    string assigned_room;
};

// 教室
struct Room {

    string room_id;

    int capacity;
};

#endif