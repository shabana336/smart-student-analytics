
from pathlib import Path
from datetime import date
import re

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Boolean, Date, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Session, relationship

from app.database import Base, engine, SessionLocal


# ==========================================
# 1. APPLICATION SETUP
# ==========================================

app = FastAPI(
    title="Student Performance Analysis System",
    description="Student management, attendance and academic analytics",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"


# ==========================================
# 2. DATABASE MODELS
# ==========================================

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    course = Column(String, nullable=False)

    attendance_records = relationship(
        "Attendance", back_populates="student",
        cascade="all, delete-orphan"
    )
    results = relationship(
        "Result", back_populates="student",
        cascade="all, delete-orphan"
    )


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    attendance_date = Column(Date, nullable=False)
    present = Column(Boolean, nullable=False)

    student = relationship("Student", back_populates="attendance_records")

    __table_args__ = (
        UniqueConstraint(
            "student_id", "attendance_date",
            name="unique_student_attendance_date"
        ),
    )


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject = Column(String, nullable=False)
    marks_obtained = Column(Float, nullable=False)
    max_marks = Column(Float, nullable=False)

    student = relationship("Student", back_populates="results")


# Create tables that do not already exist.
# This does not migrate existing database schemas.
Base.metadata.create_all(bind=engine)


# ==========================================
# 3. DATABASE SESSION
# ==========================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# 4. REQUEST SCHEMAS
# ==========================================

class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    course: str = Field(min_length=1, max_length=100)


class AttendanceCreate(BaseModel):
    student_id: int = Field(gt=0)
    attendance_date: date
    present: bool


class ResultCreate(BaseModel):
    student_id: int = Field(gt=0)
    subject: str = Field(min_length=1, max_length=100)
    marks_obtained: float = Field(ge=0)
    max_marks: float = Field(gt=0)


def validate_student(data):
    name = data.name.strip()
    email = data.email.strip().lower()
    course = data.course.strip()

    if not name or not course:
        raise HTTPException(422, "Name and course are required.")

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(422, "Enter a valid email address.")

    return name, email, course


# ==========================================
# 5. STUDENT ROUTES
# ==========================================

@app.get("/api/students")
def get_students(db: Session = Depends(get_db)):
    return db.query(Student).order_by(Student.id).all()


@app.post("/api/students", status_code=201)
def add_student(data: StudentCreate, db: Session = Depends(get_db)):
    name, email, course = validate_student(data)

    if db.query(Student).filter(Student.email == email).first():
        raise HTTPException(409, "Email already exists.")

    student = Student(name=name, email=email, course=course)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@app.put("/api/students/{student_id}")
def update_student(
    student_id: int,
    data: StudentCreate,
    db: Session = Depends(get_db),
):
    student = db.get(Student, student_id)

    if not student:
        raise HTTPException(404, "Student not found.")

    name, email, course = validate_student(data)

    duplicate = db.query(Student).filter(
        Student.email == email,
        Student.id != student_id
    ).first()

    if duplicate:
        raise HTTPException(409, "Email already exists.")

    student.name = name
    student.email = email
    student.course = course
    db.commit()
    db.refresh(student)
    return student


@app.delete("/api/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)

    if not student:
        raise HTTPException(404, "Student not found.")

    db.delete(student)
    db.commit()
    return {"message": "Student deleted successfully."}


# ==========================================
# 6. ATTENDANCE ROUTES
# ==========================================

@app.post("/api/attendance", status_code=201)
def add_attendance(
    data: AttendanceCreate,
    db: Session = Depends(get_db),
):
    if not db.get(Student, data.student_id):
        raise HTTPException(404, "Student not found.")

    existing = db.query(Attendance).filter(
        Attendance.student_id == data.student_id,
        Attendance.attendance_date == data.attendance_date,
    ).first()

    if existing:
        raise HTTPException(409, "Attendance already exists for this date.")

    record = Attendance(
        student_id=data.student_id,
        attendance_date=data.attendance_date,
        present=data.present,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/attendance")
def get_attendance(db: Session = Depends(get_db)):
    return db.query(Attendance).order_by(
        Attendance.attendance_date.desc()
    ).all()


@app.get("/api/attendance/summary")
def attendance_summary(db: Session = Depends(get_db)):
    total = db.query(Attendance).count()
    present = db.query(Attendance).filter(
        Attendance.present.is_(True)
    ).count()

    return {
        "total_students": db.query(Student).count(),
        "total_records": total,
        "present_count": present,
        "attendance_percentage": round(present * 100 / total, 2)
        if total else 0,
    }


# ==========================================
# 7. EXAMINATION RESULTS ROUTES
# ==========================================

@app.post("/api/results", status_code=201)
def add_result(data: ResultCreate, db: Session = Depends(get_db)):
    if not db.get(Student, data.student_id):
        raise HTTPException(404, "Student not found.")

    if data.marks_obtained > data.max_marks:
        raise HTTPException(422, "Marks cannot exceed maximum marks.")

    subject = data.subject.strip()
    if not subject:
        raise HTTPException(422, "Subject is required.")

    result = Result(
        student_id=data.student_id,
        subject=subject,
        marks_obtained=data.marks_obtained,
        max_marks=data.max_marks,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


@app.get("/api/results")
def get_results(db: Session = Depends(get_db)):
    return db.query(Result).order_by(Result.id.desc()).all()


@app.get("/api/results/summary")
def results_summary(db: Session = Depends(get_db)):
    students = db.query(Student).order_by(Student.id).all()
    results = db.query(Result).all()

    grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    student_percentages = {}
    subject_percentages = {}

    for result in results:
        percentage = result.marks_obtained / result.max_marks * 100

        if percentage >= 90:
            grade = "A"
        elif percentage >= 80:
            grade = "B"
        elif percentage >= 70:
            grade = "C"
        elif percentage >= 40:
            grade = "D"
        else:
            grade = "F"

        grade_counts[grade] += 1
        student_percentages.setdefault(result.student_id, []).append(percentage)
        subject_percentages.setdefault(result.subject, []).append(percentage)

    all_percentages = [
        result.marks_obtained / result.max_marks * 100
        for result in results
    ]

    student_averages = []
    for student in students:
        values = student_percentages.get(student.id, [])
        student_averages.append({
            "student_id": student.id,
            "name": student.name,
            "average": round(sum(values) / len(values), 2) if values else 0,
        })

    subject_averages = {
        subject: round(sum(values) / len(values), 2)
        for subject, values in subject_percentages.items()
    }

    return {
        "total_students": len(students),
        "total_results": len(results),
        "class_average": round(
            sum(all_percentages) / len(all_percentages), 2
        ) if all_percentages else 0,
        "grade_distribution": grade_counts,
        "subject_averages": subject_averages,
        "student_averages": student_averages,
    }


# ==========================================
# 8. HEALTH CHECK AND FRONTEND
# ==========================================

@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


# IMPORTANT: Mount static files after defining API routes.
app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)
