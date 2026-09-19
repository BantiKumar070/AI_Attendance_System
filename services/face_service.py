"""
services/face_service.py
=========================
The heart of the computer-vision pipeline. Implements the full flow:

    Capture N images -> Generate 128-d encodings -> Store in DB
    -> Build in-memory cache -> Recognize live webcam frames

Design choices:
    * Encodings are the source of truth in the database (``FaceEncoding``
      table). An in-memory + on-disk pickle cache
      (trainer/encodings.pickle) is kept purely for fast lookup during
      live recognition, and is rebuilt whenever new students are
      enrolled so the recognizer never has to hit the DB per-frame.
    * A short in-process cooldown (``_last_seen``) stops the same face
      from being re-processed on every single frame (~30 fps) — the
      database UNIQUE constraint on Attendance is the final guard
      against duplicates across restarts/processes.
"""

from __future__ import annotations

import base64
import io
import os
import pickle
import time
from typing import Dict, List, Optional, Tuple

import cv2
import face_recognition
import numpy as np
from flask import current_app
from PIL import Image

from models import FaceEncoding, Student
from utils.extensions import db
from utils.helpers import student_dataset_folder
from utils.logger import get_logger

logger = get_logger(__name__)


class FaceService:
    """Encapsulates every face-recognition related operation."""

    # In-memory cooldown tracker: {student_id: last_marked_unix_timestamp}
    # Shared at class-level so it persists across requests within one process.
    _last_seen: Dict[int, float] = {}

    # In-memory cache of (encodings_matrix, student_ids) loaded from disk/DB
    _cache: Optional[Tuple[np.ndarray, List[int]]] = None

    # ------------------------------------------------------------------
    # STEP 1: Dataset capture
    # ------------------------------------------------------------------
    def save_capture_frame(self, student: Student, image_base64: str) -> Tuple[int, Optional[str]]:
        """
        Decode a single base64-encoded webcam frame (sent from the browser
        during the "Capture 100 Images" wizard) and save it to the
        student's dataset folder, provided a face is clearly visible.

        Returns:
            (current_image_count, error_message_or_None)
        """
        try:
            header_removed = image_base64.split(",", 1)[-1]
            image_bytes = base64.b64decode(header_removed)
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            frame = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        except Exception as exc:
            logger.warning("Failed to decode capture frame: %s", exc)
            return self._current_image_count(student), "Could not decode the captured image."

        # Reject frames with no detectable face, or more than one face
        # (avoids polluting the dataset with bystanders/empty frames).
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(
            rgb_frame, model=current_app.config["FACE_DETECTION_MODEL"]
        )
        if len(face_locations) == 0:
            return self._current_image_count(student), "No face detected in frame. Please face the camera."
        if len(face_locations) > 1:
            return self._current_image_count(student), "Multiple faces detected. Only one person should be in frame."

        folder = student_dataset_folder(student.roll_number, student.name)
        os.makedirs(folder, exist_ok=True)

        next_index = self._current_image_count(student) + 1
        filename = f"img_{next_index:04d}.jpg"
        filepath = os.path.join(folder, filename)
        cv2.imwrite(filepath, frame)

        if not student.dataset_path:
            student.dataset_path = folder
            db.session.commit()

        return next_index, None

    def _current_image_count(self, student: Student) -> int:
        """Count how many dataset images already exist for this student."""
        folder = student.dataset_path or student_dataset_folder(student.roll_number, student.name)
        if not os.path.isdir(folder):
            return 0
        return len([f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))])

    def capture_progress(self, student: Student) -> Dict[str, int]:
        """Return {"captured": n, "required": N} for the capture-wizard progress bar."""
        required = current_app.config["FACE_DATASET_SAMPLES"]
        return {"captured": self._current_image_count(student), "required": required}

    # ------------------------------------------------------------------
    # STEP 2: Encoding generation
    # ------------------------------------------------------------------
    def generate_encodings_for_student(self, student: Student) -> Tuple[int, Optional[str]]:
        """
        Process every image in the student's dataset folder, extract a
        128-d face encoding from each, and persist them to the
        FaceEncoding table (replacing any previous encodings for this
        student). Rebuilds the global recognition cache afterwards.

        Returns:
            (encodings_created_count, error_message_or_None)
        """
        folder = student.dataset_path or student_dataset_folder(student.roll_number, student.name)
        if not os.path.isdir(folder):
            return 0, "No captured images found for this student. Please capture images first."

        image_files = sorted(f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png")))
        if not image_files:
            return 0, "Dataset folder is empty."

        # Remove old encodings for this student so re-running enrollment
        # doesn't accumulate stale/duplicate vectors.
        FaceEncoding.query.filter_by(student_id=student.id).delete()

        created = 0
        for filename in image_files:
            filepath = os.path.join(folder, filename)
            image = face_recognition.load_image_file(filepath)
            face_locations = face_recognition.face_locations(
                image, model=current_app.config["FACE_DETECTION_MODEL"]
            )
            if not face_locations:
                continue  # Skip frames where a face can't be re-detected

            encodings = face_recognition.face_encodings(image, known_face_locations=face_locations)
            if not encodings:
                continue

            record = FaceEncoding(student_id=student.id, source_image=filename)
            record.set_vector(encodings[0])
            db.session.add(record)
            created += 1

        if created == 0:
            db.session.rollback()
            return 0, "No usable faces could be extracted from the captured images."

        student.face_registered = True
        db.session.commit()

        self.rebuild_encoding_cache()
        logger.info("Generated %d encodings for student_id=%s", created, student.id)
        return created, None

    # ------------------------------------------------------------------
    # STEP 3: Encoding cache (DB -> memory/pickle) for fast recognition
    # ------------------------------------------------------------------
    def rebuild_encoding_cache(self) -> int:
        """
        Rebuild trainer/encodings.pickle from the FaceEncoding table and
        refresh the in-memory cache. Call this after any enrollment
        change (new student, re-encoded student, deleted student).

        Returns:
            Total number of encoding vectors cached.
        """
        rows = FaceEncoding.query.all()
        if not rows:
            FaceService._cache = (np.empty((0, 128)), [])
        else:
            matrix = np.vstack([row.get_vector() for row in rows])
            student_ids = [row.student_id for row in rows]
            FaceService._cache = (matrix, student_ids)

        encodings_path = current_app.config["ENCODINGS_FILE"]
        os.makedirs(os.path.dirname(encodings_path), exist_ok=True)
        with open(encodings_path, "wb") as f:
            pickle.dump(FaceService._cache, f)

        count = len(rows)
        logger.info("Encoding cache rebuilt with %d vectors.", count)
        return count

    def _get_cache(self) -> Tuple[np.ndarray, List[int]]:
        """Return the in-memory cache, loading from disk or DB if needed."""
        if FaceService._cache is not None:
            return FaceService._cache

        encodings_path = current_app.config["ENCODINGS_FILE"]
        if os.path.isfile(encodings_path):
            try:
                with open(encodings_path, "rb") as f:
                    FaceService._cache = pickle.load(f)
                    return FaceService._cache
            except Exception:  # pragma: no cover - corrupt cache falls back to rebuild
                logger.exception("Failed to load encodings.pickle, rebuilding from DB.")

        self.rebuild_encoding_cache()
        return FaceService._cache  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # STEP 4: Real-time recognition
    # ------------------------------------------------------------------
    def recognize_frame(self, frame_bgr: np.ndarray) -> List[Dict]:
        """
        Detect and recognize every face in a single BGR frame (as
        produced by OpenCV / a decoded webcam snapshot).

        Returns:
            A list of dicts, one per detected face:
                {
                    "student_id": int | None,   # None if unrecognized
                    "confidence": float,        # 0.0 - 1.0 (higher = better match)
                    "box": (top, right, bottom, left),
                }
        """
        known_matrix, known_ids = self._get_cache()

        # Resize for speed, then scale coordinates back up afterwards.
        target_width = current_app.config["FACE_RESIZE_WIDTH"]
        scale = target_width / frame_bgr.shape[1] if frame_bgr.shape[1] > target_width else 1.0
        small_frame = cv2.resize(frame_bgr, (0, 0), fx=scale, fy=scale) if scale != 1.0 else frame_bgr

        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small, model=current_app.config["FACE_DETECTION_MODEL"])
        face_encodings = face_recognition.face_encodings(rgb_small, known_face_locations=face_locations)

        tolerance = current_app.config["FACE_RECOGNITION_TOLERANCE"]
        results: List[Dict] = []

        for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
            student_id = None
            confidence = 0.0

            if known_matrix.shape[0] > 0:
                distances = face_recognition.face_distance(known_matrix, encoding)
                best_index = int(np.argmin(distances))
                best_distance = float(distances[best_index])

                if best_distance <= tolerance:
                    student_id = known_ids[best_index]
                    confidence = max(0.0, 1.0 - best_distance)

            # Scale bounding box back to original frame size
            box = (
                int(top / scale), int(right / scale), int(bottom / scale), int(left / scale)
            )
            results.append({"student_id": student_id, "confidence": round(confidence, 3), "box": box})

        return results

    # ------------------------------------------------------------------
    # Cooldown helper used by AttendanceService to avoid re-processing
    # the same student's face on every frame within a short window.
    # ------------------------------------------------------------------
    def is_in_cooldown(self, student_id: int, cooldown_seconds: int = 8) -> bool:
        """Return True if this student was successfully recognized very recently."""
        last = FaceService._last_seen.get(student_id)
        if last is None:
            return False
        return (time.time() - last) < cooldown_seconds

    def mark_seen(self, student_id: int) -> None:
        """Record that this student was just recognized (for cooldown purposes)."""
        FaceService._last_seen[student_id] = time.time()
