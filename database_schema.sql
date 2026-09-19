-- ============================================================================
-- AI-Powered Automatic Attendance System Using Face Recognition
-- Database Schema Reference (SQLite syntax; MySQL notes inline)
--
-- NOTE: In normal operation this schema is created automatically by
-- SQLAlchemy (see app.py -> db.create_all()). This file is provided as
-- human-readable documentation and for manual inspection / migration to
-- MySQL. To move to MySQL, change AUTOINCREMENT -> AUTO_INCREMENT and
-- set DATABASE_URL to a mysql+pymysql:// connection string in config.py.
-- ============================================================================

CREATE TABLE IF NOT EXISTS admins (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        VARCHAR(80)  NOT NULL UNIQUE,
    email           VARCHAR(120) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(120) NOT NULL,
    role            VARCHAR(20)  NOT NULL DEFAULT 'admin',
    is_active       BOOLEAN      NOT NULL DEFAULT 1,
    last_login_at   DATETIME,
    created_at      DATETIME     NOT NULL,
    updated_at      DATETIME     NOT NULL
);

CREATE TABLE IF NOT EXISTS class_rooms (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            VARCHAR(100) NOT NULL,
    section         VARCHAR(20),
    academic_year   VARCHAR(20),
    is_active       BOOLEAN      NOT NULL DEFAULT 1,
    created_at      DATETIME     NOT NULL,
    updated_at      DATETIME     NOT NULL
);

CREATE TABLE IF NOT EXISTS subjects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            VARCHAR(120) NOT NULL,
    code            VARCHAR(30)  NOT NULL UNIQUE,
    class_id        INTEGER REFERENCES class_rooms(id),
    is_active       BOOLEAN      NOT NULL DEFAULT 1,
    created_at      DATETIME     NOT NULL,
    updated_at      DATETIME     NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_number     VARCHAR(30)  NOT NULL UNIQUE,
    name            VARCHAR(120) NOT NULL,
    email           VARCHAR(120) UNIQUE,
    phone           VARCHAR(20),
    gender          VARCHAR(10),
    class_id        INTEGER REFERENCES class_rooms(id),
    dataset_path    VARCHAR(255),
    photo_path      VARCHAR(255),
    face_registered BOOLEAN      NOT NULL DEFAULT 0,
    is_active       BOOLEAN      NOT NULL DEFAULT 1,
    created_at      DATETIME     NOT NULL,
    updated_at      DATETIME     NOT NULL
);

-- Each row = one 128-dimension face_recognition encoding vector,
-- stored as raw float64 bytes (128 * 8 = 1024 bytes per encoding).
CREATE TABLE IF NOT EXISTS face_encodings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    encoding        BLOB    NOT NULL,
    source_image    VARCHAR(255),
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id        INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id        INTEGER REFERENCES subjects(id),
    class_id          INTEGER REFERENCES class_rooms(id),
    attendance_date   DATE    NOT NULL,
    time_in           TIME    NOT NULL,
    status            VARCHAR(20) NOT NULL DEFAULT 'present',
    marked_by         VARCHAR(30) NOT NULL DEFAULT 'face_recognition',
    confidence_score  FLOAT,
    created_at        DATETIME NOT NULL,
    updated_at        DATETIME NOT NULL,
    -- Duplicate-attendance prevention: one row per student/subject/day
    UNIQUE (student_id, subject_id, attendance_date)
);

CREATE TABLE IF NOT EXISTS system_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    actor         VARCHAR(120),
    action        VARCHAR(100) NOT NULL,
    description   TEXT,
    level         VARCHAR(20)  NOT NULL DEFAULT 'info',
    ip_address    VARCHAR(45),
    created_at    DATETIME NOT NULL,
    updated_at    DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    key           VARCHAR(100) NOT NULL UNIQUE,
    value         TEXT,
    description   VARCHAR(255),
    created_at    DATETIME NOT NULL,
    updated_at    DATETIME NOT NULL
);

-- ============================================================================
-- Helpful indexes (in addition to the UNIQUE / FK indexes created above)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(attendance_date);
CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_face_encodings_student ON face_encodings(student_id);
CREATE INDEX IF NOT EXISTS idx_students_roll_number ON students(roll_number);
