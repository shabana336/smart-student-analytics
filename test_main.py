
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base


@pytest.fixture
def client():
    # Use a separate temporary in-memory database for testing.
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_get_db

    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_health_check(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_and_list_student(client):
    student = {
        "name": "Test Student",
        "email": "test@example.com",
        "course": "MCA",
    }

    response = client.post("/api/students", json=student)

    assert response.status_code == 201
    assert response.json()["name"] == "Test Student"

    response = client.get("/api/students")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["email"] == "test@example.com"


def test_duplicate_student_email(client):
    student = {
        "name": "Test Student",
        "email": "duplicate@example.com",
        "course": "MCA",
    }

    first = client.post("/api/students", json=student)
    second = client.post("/api/students", json=student)

    assert first.status_code == 201
    assert second.status_code == 409


def test_invalid_student_email(client):
    student = {
        "name": "Test Student",
        "email": "invalid-email",
        "course": "MCA",
    }

    response = client.post("/api/students", json=student)

    assert response.status_code == 422


def test_attendance_api(client):
    student = client.post(
        "/api/students",
        json={
            "name": "Attendance Student",
            "email": "attendance@example.com",
            "course": "MCA",
        },
    )

    student_id = student.json()["id"]

    response = client.post(
        "/api/attendance",
        json={
            "student_id": student_id,
            "attendance_date": "2026-10-26",
            "present": True,
        },
    )

    assert response.status_code == 201

    summary = client.get("/api/attendance/summary")

    assert summary.status_code == 200
    assert summary.json()["total_records"] == 1
    assert summary.json()["present_count"] == 1
    assert summary.json()["attendance_percentage"] == 100


def test_attendance_for_missing_student(client):
    response = client.post(
        "/api/attendance",
        json={
            "student_id": 9999,
            "attendance_date": "2026-10-26",
            "present": True,
        },
    )

    assert response.status_code == 404


def test_exam_result_and_summary(client):
    student = client.post(
        "/api/students",
        json={
            "name": "Result Student",
            "email": "result@example.com",
            "course": "MCA",
        },
    )

    student_id = student.json()["id"]

    response = client.post(
        "/api/results",
        json={
            "student_id": student_id,
            "subject": "Computer Networks",
            "marks_obtained": 85,
            "max_marks": 100,
        },
    )

    assert response.status_code == 201

    summary = client.get("/api/results/summary")

    assert summary.status_code == 200
    assert summary.json()["total_students"] == 1
    assert summary.json()["total_results"] == 1
    assert summary.json()["class_average"] == 85


def test_marks_cannot_exceed_maximum(client):
    student = client.post(
        "/api/students",
        json={
            "name": "Marks Student",
            "email": "marks@example.com",
            "course": "MCA",
        },
    )

    student_id = student.json()["id"]

    response = client.post(
        "/api/results",
        json={
            "student_id": student_id,
            "subject": "C Programming",
            "marks_obtained": 110,
            "max_marks": 100,
        },
    )

    assert response.status_code == 422


def test_result_for_missing_student(client):
    response = client.post(
        "/api/results",
        json={
            "student_id": 9999,
            "subject": "Database Management",
            "marks_obtained": 80,
            "max_marks": 100,
        },
    )

    assert response.status_code == 404
