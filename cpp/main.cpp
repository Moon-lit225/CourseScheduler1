#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <algorithm>
#include <iomanip>

#include "model.h"

using namespace std;

bool hasTimeConflict(const Course& c1, const Course& c2) {
    if (c1.day != c2.day) return false;
    
    int c1_end = c1.start + c1.length;
    int c2_end = c2.start + c2.length;
    
    return !(c1_end <= c2.start || c2_end <= c1.start);
}

bool roomIsAvailable(const vector<Course>& assignedCourses, const Course& newCourse, const string& roomId) {
    for (const Course& c : assignedCourses) {
        if (c.assigned_room == roomId && hasTimeConflict(c, newCourse)) {
            return false;
        }
    }
    return true;
}

double calculateFitness(const vector<Course>& courses, const vector<Room>& rooms) {
    int conflicts = 0;
    int assignedCount = 0;
    vector<int> roomUsage(rooms.size(), 0);
    
    for (size_t i = 0; i < courses.size(); i++) {
        if (courses[i].assigned_room == "Unassigned") continue;
        assignedCount++;
        
        for (size_t j = i + 1; j < courses.size(); j++) {
            if (courses[j].assigned_room == "Unassigned") continue;
            
            if (courses[i].assigned_room == courses[j].assigned_room && hasTimeConflict(courses[i], courses[j])) {
                conflicts++;
            }
        }
        
        for (size_t k = 0; k < rooms.size(); k++) {
            if (rooms[k].room_id == courses[i].assigned_room) {
                roomUsage[k] += courses[i].length;
                break;
            }
        }
    }
    
    int totalTimeSlots = 0;
    for (int usage : roomUsage) {
        totalTimeSlots += usage;
    }
    
    double avgUtilization = rooms.empty() ? 0.0 : (double)totalTimeSlots / (rooms.size() * 840);
    
    double conflictPenalty = conflicts * 1000.0;
    double utilizationBonus = avgUtilization * 100.0;
    double assignmentBonus = assignedCount * 10.0;
    
    return -conflictPenalty + utilizationBonus + assignmentBonus;
}

string getDayName(const string& dayCode) {
    vector<string> days;
    if (dayCode.size() >= 1 && dayCode[0] == '1') days.push_back("Mon");
    if (dayCode.size() >= 2 && dayCode[1] == '1') days.push_back("Tue");
    if (dayCode.size() >= 3 && dayCode[2] == '1') days.push_back("Wed");
    if (dayCode.size() >= 4 && dayCode[3] == '1') days.push_back("Thu");
    if (dayCode.size() >= 5 && dayCode[4] == '1') days.push_back("Fri");
    if (dayCode.size() >= 6 && dayCode[5] == '1') days.push_back("Sat");
    if (dayCode.size() >= 7 && dayCode[6] == '1') days.push_back("Sun");
    
    if (days.empty()) return dayCode;
    
    string result;
    for (size_t i = 0; i < days.size(); i++) {
        if (i > 0) result += "+";
        result += days[i];
    }
    return result;
}

string formatTime(int minutes) {
    int hours = minutes / 60;
    int mins = minutes % 60;
    ostringstream oss;
    oss << setw(2) << setfill('0') << hours << ":" << setw(2) << setfill('0') << mins;
    return oss.str();
}

int main() {
    vector<Course> courses;
    vector<Room> rooms;

    ifstream courseFile("../output/courses.csv");
    if (!courseFile.is_open()) {
        cout << "Failed to open courses.csv!" << endl;
        return 1;
    }

    string line;
    getline(courseFile, line);

    while (getline(courseFile, line)) {
        if (line.empty()) continue;

        stringstream ss(line);
        Course c;
        string temp;

        getline(ss, c.course_id, ',');
        
        getline(ss, temp, ',');
        c.student_limit = temp.empty() ? 0 : stoi(temp);

        getline(ss, c.day, ',');

        getline(ss, temp, ',');
        c.start = temp.empty() ? 0 : stoi(temp);

        getline(ss, temp, ',');
        c.length = temp.empty() ? 0 : stoi(temp);

        c.assigned_room = "Unassigned";
        courses.push_back(c);
    }
    courseFile.close();

    ifstream roomFile("../data/rooms.csv");
    if (!roomFile.is_open()) {
        cout << "Failed to open rooms.csv!" << endl;
        return 1;
    }

    getline(roomFile, line);

    while (getline(roomFile, line)) {
        if (line.empty()) continue;

        stringstream ss(line);
        Room r;
        string temp;

        getline(ss, r.room_id, ',');

        getline(ss, temp, ',');
        r.capacity = temp.empty() ? 0 : stoi(temp);

        rooms.push_back(r);
    }
    roomFile.close();

    cout << "Number of courses: " << courses.size() << endl;
    cout << "Number of rooms: " << rooms.size() << endl;

    sort(courses.begin(), courses.end(), [](const Course& a, const Course& b) {
        if (a.student_limit != b.student_limit) {
            return a.student_limit > b.student_limit;
        }
        if (a.length != b.length) {
            return a.length > b.length;
        }
        return a.start < b.start;
    });

    for (size_t i = 0; i < courses.size(); i++) {
        int bestRoomIndex = -1;
        int minCapacity = 999999;

        for (size_t j = 0; j < rooms.size(); j++) {
            if (rooms[j].capacity < courses[i].student_limit) {
                continue;
            }

            if (!roomIsAvailable(courses, courses[i], rooms[j].room_id)) {
                continue;
            }

            if (rooms[j].capacity < minCapacity) {
                minCapacity = rooms[j].capacity;
                bestRoomIndex = j;
            }
        }

        if (bestRoomIndex != -1) {
            courses[i].assigned_room = rooms[bestRoomIndex].room_id;
        }
    }

    cout << "\nStarting conflict detection...\n" << endl;

    int conflictCount = 0;

    for (size_t i = 0; i < courses.size(); i++) {
        for (size_t j = i + 1; j < courses.size(); j++) {
            if (courses[i].assigned_room == "Unassigned" || courses[j].assigned_room == "Unassigned") {
                continue;
            }

            if (courses[i].assigned_room == courses[j].assigned_room && hasTimeConflict(courses[i], courses[j])) {
                conflictCount++;
            }
        }
    }

    double fitness = calculateFitness(courses, rooms);

    cout << "\n=== Schedule Statistics ===" << endl;
    cout << "Total courses: " << courses.size() << endl;
    
    int assignedCount = 0;
    for (const Course& c : courses) {
        if (c.assigned_room != "Unassigned") assignedCount++;
    }
    cout << "Assigned courses: " << assignedCount << endl;
    cout << "Unassigned courses: " << courses.size() - assignedCount << endl;
    cout << "Total conflicts: " << conflictCount << endl;
    cout << "Fitness: " << fixed << setprecision(2) << fitness << endl;

    ofstream resultFile("../output/schedule_result.csv");
    if (!resultFile.is_open()) {
        cout << "Failed to create schedule_result.csv!" << endl;
        return 1;
    }

    resultFile << "course_id,student_limit,day,day_name,start_time,end_time,length,room,room_capacity" << endl;

    for (const Course& c : courses) {
        string roomCapacity = "";
        for (const Room& r : rooms) {
            if (r.room_id == c.assigned_room) {
                roomCapacity = to_string(r.capacity);
                break;
            }
        }
        
        resultFile << c.course_id << ","
                   << c.student_limit << ","
                   << c.day << ","
                   << getDayName(c.day) << ","
                   << formatTime(c.start) << ","
                   << formatTime(c.start + c.length) << ","
                   << c.length << ","
                   << c.assigned_room << ","
                   << roomCapacity << endl;
    }

    resultFile.close();

    cout << "\nSchedule results exported to: ../output/schedule_result.csv" << endl;

    return 0;
}