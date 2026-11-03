
"use strict";

// ============================================
// STUDENT PERFORMANCE - FRONTEND
// ============================================

const $ = (id) => document.getElementById(id);

const studentForm = $("studentForm");
const resultForm = $("resultForm");
const studentTable = $("studentTable");
const resultsTable = $("resultsTable");
const message = $("message");

let subjectChartInstance = null;
let studentChartInstance = null;
let distributionChartInstance = null;

function showMessage(text, isError = false) {
    message.textContent = text;
    message.style.color = isError ? "#dc2626" : "#15803d";
}

async function api(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            ...(options.body ? { "Content-Type": "application/json" } : {}),
            ...options.headers
        }
    });

    const data = response.status === 204
        ? null
        : await response.json().catch(() => ({}));

    if (!response.ok) {
        const detail = data?.detail;
        const errorText = Array.isArray(detail)
            ? detail.map(item => item.msg).join(", ")
            : detail || `Request failed (${response.status})`;

        throw new Error(errorText);
    }

    return data;
}

function makeCell(row, value) {
    const cell = document.createElement("td");
    cell.textContent = value ?? "";
    row.appendChild(cell);
    return cell;
}

function gradeFor(percentage) {
    if (percentage >= 90) return "A";
    if (percentage >= 80) return "B";
    if (percentage >= 70) return "C";
    if (percentage >= 40) return "D";
    return "F";
}

// ============================================
// STUDENT RECORDS
// ============================================

async function loadStudents() {
    studentTable.innerHTML =
        "<tr><td colspan='5'>Loading students...</td></tr>";

    try {
        const students = await api("/api/students");
        $("totalStudents").textContent = students.length;
        studentTable.innerHTML = "";

        if (!students.length) {
            studentTable.innerHTML =
                "<tr><td colspan='5'>No students added yet.</td></tr>";
            return;
        }

        students.forEach(student => {
            const row = document.createElement("tr");

            makeCell(row, student.id);
            makeCell(row, student.name);
            makeCell(row, student.email);
            makeCell(row, student.course);

            const actions = makeCell(row, "");

            const editButton = document.createElement("button");
            editButton.type = "button";
            editButton.textContent = "Edit";
            editButton.addEventListener("click", () => editStudent(student));

            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.textContent = "Delete";
            deleteButton.className = "delete-button";
            deleteButton.addEventListener(
                "click", () => deleteStudent(student.id)
            );

            actions.append(editButton, deleteButton);
            studentTable.appendChild(row);
        });
    } catch (error) {
        studentTable.innerHTML =
            "<tr><td colspan='5'>Could not load student records.</td></tr>";
        showMessage(error.message, true);
    }
}

studentForm.addEventListener("submit", async event => {
    event.preventDefault();

    const student = {
        name: $("name").value.trim(),
        email: $("email").value.trim(),
        course: $("course").value.trim()
    };

    if (!student.name || !student.email || !student.course) {
        showMessage("Please complete all student fields.", true);
        return;
    }

    try {
        await api("/api/students", {
            method: "POST",
            body: JSON.stringify(student)
        });

        studentForm.reset();
        showMessage("Student added successfully.");
        await refreshDashboard();
    } catch (error) {
        showMessage(error.message, true);
    }
});

async function editStudent(student) {
    const name = prompt("Student name:", student.name);
    if (name === null) return;

    const email = prompt("Student email:", student.email);
    if (email === null) return;

    const course = prompt("Student course:", student.course);
    if (course === null) return;

    if (!name.trim() || !email.trim() || !course.trim()) {
        showMessage("All student fields are required.", true);
        return;
    }

    try {
        await api(`/api/students/${student.id}`, {
            method: "PUT",
            body: JSON.stringify({
                name: name.trim(),
                email: email.trim(),
                course: course.trim()
            })
        });

        showMessage("Student updated successfully.");
        await refreshDashboard();
    } catch (error) {
        showMessage(error.message, true);
    }
}

async function deleteStudent(studentId) {
    if (!confirm("Delete this student and their related records?")) return;

    try {
        await api(`/api/students/${studentId}`, {
            method: "DELETE"
        });

        showMessage("Student deleted successfully.");
        await refreshDashboard();
    } catch (error) {
        showMessage(error.message, true);
    }
}

// ============================================
// EXAMINATION RESULTS
// ============================================

resultForm.addEventListener("submit", async event => {
    event.preventDefault();

    const studentId = Number($("resultStudentId").value);
    const marks = Number($("marksObtained").value);
    const maximum = Number($("maxMarks").value);
    const subject = $("subject").value.trim();

    if (!Number.isInteger(studentId) || studentId <= 0) {
        showMessage("Enter a valid student ID.", true);
        return;
    }

    if (!subject || !Number.isFinite(marks) ||
        !Number.isFinite(maximum) || marks < 0 ||
        maximum <= 0 || marks > maximum) {
        showMessage("Check the subject and marks entered.", true);
        return;
    }

    try {
        await api("/api/results", {
            method: "POST",
            body: JSON.stringify({
                student_id: studentId,
                subject,
                marks_obtained: marks,
                max_marks: maximum
            })
        });

        resultForm.reset();
        $("maxMarks").value = "100";
        showMessage("Examination result saved successfully.");
        await refreshDashboard();
    } catch (error) {
        showMessage(error.message, true);
    }
});

async function loadResults() {
    const results = await api("/api/results");
    resultsTable.innerHTML = "";

    if (!results.length) {
        resultsTable.innerHTML =
            "<tr><td colspan='6'>No examination results available.</td></tr>";
        return;
    }

    results.forEach(result => {
        const row = document.createElement("tr");
        const percentage =
            result.marks_obtained / result.max_marks * 100;

        makeCell(row, result.student_id);
        makeCell(row, result.subject);
        makeCell(row, result.marks_obtained);
        makeCell(row, result.max_marks);
        makeCell(row, `${percentage.toFixed(2)}%`);
        makeCell(row, gradeFor(percentage));

        resultsTable.appendChild(row);
    });
}

// ============================================
// ATTENDANCE SUMMARY
// ============================================

async function loadAttendance() {
    try {
        const data = await api("/api/attendance/summary");

        $("attendance").textContent =
            `${data.attendance_percentage}%`;
    } catch (error) {
        console.error("Attendance summary:", error.message);
        $("attendance").textContent = "Unavailable";
    }
}

// ============================================
// CHARTS
// ============================================

function drawChart(canvasId, oldChart, type, labels, values, label) {
    if (oldChart) oldChart.destroy();

    const canvas = $(canvasId);

    if (typeof Chart === "undefined") {
        throw new Error("Chart.js failed to load. Check your internet connection.");
    }

    return new Chart(canvas, {
        type,
        data: {
            labels,
            datasets: [{
                label,
                data: values,
                borderWidth: 2,
                backgroundColor: [
                    "#2563eb", "#16a34a", "#f59e0b",
                    "#8b5cf6", "#ef4444", "#0891b2"
                ],
                borderColor: "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: type === "bar" ? {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: "Percentage"
                    }
                }
            } : {},
            plugins: {
                legend: { display: type === "doughnut" }
            }
        }
    });
}

async function loadAnalytics() {
    const data = await api("/api/results/summary");

    $("classAverage").textContent = `${data.class_average}%`;
    $("totalResults").textContent = data.total_results;

    const subjects = data.subject_averages || {};
    subjectChartInstance = drawChart(
        "subjectChart",
        subjectChartInstance,
        "bar",
        Object.keys(subjects),
        Object.values(subjects),
        "Average marks (%)"
    );

    const students = data.student_averages || [];
    studentChartInstance = drawChart(
        "studentChart",
        studentChartInstance,
        "bar",
        students.map(item => item.name),
        students.map(item => item.average),
        "Average marks (%)"
    );

    const grades = data.grade_distribution || {};
    distributionChartInstance = drawChart(
        "distributionChart",
        distributionChartInstance,
        "doughnut",
        Object.keys(grades),
        Object.values(grades),
        "Grade count"
    );

    $("chartMessage").textContent = data.total_results
        ? "Academic analytics updated successfully."
        : "Add examination results to populate your charts.";
}

// ============================================
// DASHBOARD REFRESH
// ============================================

async function refreshDashboard() {
    await loadStudents();
    await loadAttendance();

    try {
        await loadResults();
        await loadAnalytics();
    } catch (error) {
        console.error("Analytics loading error:", error);
        $("chartMessage").textContent = error.message;
        showMessage(
            "Some analytics could not load. Check the backend API.",
            true
        );
    }
}

$("refreshButton").addEventListener("click", refreshDashboard);

document.addEventListener("DOMContentLoaded", refreshDashboard);
