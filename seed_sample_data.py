"""
seed_sample_data.py
====================
Populates the database with sample classes, subjects, and students so
the dashboard/UI isn't empty on a fresh install. Does NOT create face
encodings (that requires real webcam captures) — newly seeded students
will show as "Pending" enrollment until you run them through the
Capture wizard in the UI.

Usage:
    python seed_sample_data.py
"""

from __future__ import annotations

from app import create_app
from models import ClassRoom, Student, Subject
from utils.extensions import db


def run() -> None:
    app = create_app()
    with app.app_context():
        if ClassRoom.query.first():
            print("Sample data already exists — skipping seed.")
            return

        # --- Classes ---
        cs_year2 = ClassRoom(name="BSc Computer Science", section="A", academic_year="2025-2026")
        it_year1 = ClassRoom(name="BSc Information Technology", section="B", academic_year="2025-2026")
        db.session.add_all([cs_year2, it_year1])
        db.session.commit()

        # --- Subjects ---
        subjects = [
            Subject(name="Data Structures", code="CS201", class_id=cs_year2.id),
            Subject(name="Operating Systems", code="CS202", class_id=cs_year2.id),
            Subject(name="Web Technologies", code="IT101", class_id=it_year1.id),
        ]
        db.session.add_all(subjects)
        db.session.commit()

        # --- Students ---
        students = [
            Student(roll_number="CS-2026-001", name="Aarav Sharma", email="aarav.sharma@example.com", gender="Male", class_id=cs_year2.id),
            Student(roll_number="CS-2026-002", name="Priya Verma", email="priya.verma@example.com", gender="Female", class_id=cs_year2.id),
            Student(roll_number="CS-2026-003", name="Rohan Gupta", email="rohan.gupta@example.com", gender="Male", class_id=cs_year2.id),
            Student(roll_number="IT-2026-001", name="Sneha Iyer", email="sneha.iyer@example.com", gender="Female", class_id=it_year1.id),
            Student(roll_number="IT-2026-002", name="Karan Mehta", email="karan.mehta@example.com", gender="Male", class_id=it_year1.id),
        ]
        db.session.add_all(students)
        db.session.commit()

        print(f"Seeded {len(students)} students, {len(subjects)} subjects, and 2 classes.")
        print("Go to the Students page and use 'Capture' to enroll their faces.")


if __name__ == "__main__":
    run()
