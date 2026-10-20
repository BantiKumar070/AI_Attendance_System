# # """
# # controllers/face_controller.py
# # ===============================
# # Wires the live-recognition endpoint together: decode an incoming
# # webcam frame -> FaceService.recognize_frame() -> for every confidently
# # recognized face, AttendanceService.mark_attendance().

# # This is the controller backing the "Real-time Face Recognition" and
# # "Automatic Attendance" features.
# # """

# # from __future__ import annotations

# # import base64
# # import io
# # from typing import Dict, List, Optional

# # import cv2
# # import numpy as np
# # from PIL import Image

# # from models import Student
# # from services.attendance_service import AttendanceService
# # from services.face_service import FaceService


# # class FaceController:
# #     """Coordinates the capture -> recognize -> mark-attendance pipeline."""

# #     def __init__(self) -> None:
# #         self.face_service = FaceService()
# #         self.attendance_service = AttendanceService()

# #     def recognize_and_mark(self, image_base64: str, subject_id: Optional[int] = None) -> List[Dict]:
# #         """
# #         Decode a single webcam frame, recognize every face in it, and
# #         automatically mark attendance for confidently-matched students
# #         (respecting the cooldown to avoid duplicate processing).

# #         Returns:
# #             A list of per-face result dicts ready to be sent back to the
# #             browser as JSON, e.g.:
# #                 [{"name": "John Doe", "roll_number": "CS001",
# #                   "confidence": 0.82, "box": [t,r,b,l], "status": "marked"}]
# #         """
# #         frame = self._decode_frame(image_base64)
# #         if frame is None:
# #             return []

# #         detections = self.face_service.recognize_frame(frame)
# #         results: List[Dict] = []

# #         for detection in detections:
# #             student_id = detection["student_id"]
# #             box = detection["box"]
# #             confidence = detection["confidence"]

# #             if student_id is None:
# #                 results.append({"name": "Unknown", "roll_number": None, "confidence": confidence, "box": box, "status": "unknown"})
# #                 continue

# #             student = Student.query.get(student_id)
# #             if student is None:
# #                 continue

# #             if self.face_service.is_in_cooldown(student_id):
# #                 results.append(
# #                     {"name": student.name, "roll_number": student.roll_number, "confidence": confidence, "box": box, "status": "cooldown"}
# #                 )
# #                 continue

# #             record, created, error = self.attendance_service.mark_attendance(
# #                 student_id, subject_id=subject_id, confidence=confidence
# #             )
# #             self.face_service.mark_seen(student_id)

# #             status = "marked" if created else ("already_marked" if record else "error")
# #             results.append(
# #                 {
# #                     "name": student.name,
# #                     "roll_number": student.roll_number,
# #                     "confidence": confidence,
# #                     "box": box,
# #                     "status": status,
# #                     "error": error,
# #                 }
# #             )

# #         return results

# #     @staticmethod
# #     def _decode_frame(image_base64: str) -> Optional[np.ndarray]:
# #         """Decode a base64 data-URL (from <canvas>.toDataURL()) into a BGR numpy frame."""
# #         try:
# #             header_removed = image_base64.split(",", 1)[-1]
# #             image_bytes = base64.b64decode(header_removed)
# #             pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
# #             return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
# #         except Exception:
# #             return None





# """
# controllers/face_controller.py
# ===============================

# Coordinates live face recognition and attendance marking.

# Workflow:
# 1. Decode the incoming webcam frame.
# 2. Recognize faces using FaceService.
# 3. Check whether attendance is already marked for the selected subject.
# 4. Mark new attendance when appropriate.
# 5. Return the recognition result and status to the frontend.

# Duplicate attendance prevention remains handled by AttendanceService
# and the database's existing uniqueness constraint.
# """

# from __future__ import annotations

# import base64
# import io
# from datetime import date
# from typing import Dict, List, Optional

# import cv2
# import numpy as np
# from PIL import Image

# from models import Attendance, Student
# from services.attendance_service import AttendanceService
# from services.face_service import FaceService


# class FaceController:
#     """Coordinates face recognition and attendance marking."""

#     def __init__(self) -> None:
#         self.face_service = FaceService()
#         self.attendance_service = AttendanceService()

#     def recognize_and_mark(
#         self,
#         image_base64: str,
#         subject_id: Optional[int] = None,
#     ) -> List[Dict]:
#         """
#         Recognize faces in a webcam frame and mark attendance.

#         Returns a list of dictionaries containing:
#         - name
#         - roll_number
#         - confidence
#         - box
#         - status
#         - message
#         """

#         frame = self._decode_frame(image_base64)

#         if frame is None:
#             return []

#         detections = self.face_service.recognize_frame(frame)
#         results: List[Dict] = []

#         for detection in detections:
#             student_id = detection["student_id"]
#             box = detection["box"]
#             confidence = detection["confidence"]

#             # Handle an unrecognized face.
#             if student_id is None:
#                 results.append(
#                     {
#                         "name": "Unknown",
#                         "roll_number": None,
#                         "confidence": confidence,
#                         "box": box,
#                         "status": "unknown",
#                         "message": "Face not recognized.",
#                     }
#                 )
#                 continue

#             # Ensure that the recognized student still exists.
#             student = Student.query.get(student_id)

#             if student is None:
#                 continue

#             # Check the cooldown before doing another attendance operation.
#             #
#             # Important:
#             # If the student is in cooldown, check whether attendance
#             # exists for THIS subject and today's date.
#             #
#             # Previously, returning "cooldown" here could prevent the
#             # frontend from learning that attendance was already marked.
#             if self.face_service.is_in_cooldown(student_id):
#                 existing_record = Attendance.query.filter_by(
#                     student_id=student_id,
#                     subject_id=subject_id,
#                     attendance_date=date.today(),
#                 ).first()

#                 if existing_record is not None:
#                     if existing_record.time_in:
#                         marked_time = existing_record.time_in.strftime(
#                             "%I:%M %p"
#                         )

#                         message = (
#                             "Attendance already marked for this subject "
#                             f"today at {marked_time}."
#                         )
#                     else:
#                         message = (
#                             "Attendance already marked for this subject today."
#                         )

#                     results.append(
#                         {
#                             "name": student.name,
#                             "roll_number": student.roll_number,
#                             "confidence": confidence,
#                             "box": box,
#                             "status": "already_marked",
#                             "message": message,
#                         }
#                     )
#                     continue

#                 # There is no attendance record for the selected subject.
#                 # Do not continue here: allow the regular attendance
#                 # service below to process this student and subject.

#             # Mark attendance through the existing service.
#             #
#             # AttendanceService remains responsible for:
#             # - checking existing records
#             # - preventing duplicate records
#             # - handling database uniqueness conflicts
#             record, created, error = (
#                 self.attendance_service.mark_attendance(
#                     student_id,
#                     subject_id=subject_id,
#                     confidence=confidence,
#                 )
#             )

#             # Preserve the existing cooldown behavior.
#             self.face_service.mark_seen(student_id)

#             # Determine the result status and user-facing message.
#             if created:
#                 status = "marked"
#                 message = "Attendance marked successfully."

#             elif record is not None:
#                 status = "already_marked"

#                 if record.time_in:
#                     marked_time = record.time_in.strftime("%I:%M %p")

#                     message = (
#                         "Attendance already marked for this subject "
#                         f"today at {marked_time}."
#                     )
#                 else:
#                     message = (
#                         "Attendance already marked for this subject today."
#                     )

#             else:
#                 status = "error"
#                 message = error or "Unable to mark attendance."

#             # Preserve the existing response fields and add a message
#             # field for frontend notification handling.
#             results.append(
#                 {
#                     "name": student.name,
#                     "roll_number": student.roll_number,
#                     "confidence": confidence,
#                     "box": box,
#                     "status": status,
#                     "message": message,
#                     "error": error,
#                 }
#             )

#         return results

#     @staticmethod
#     def _decode_frame(image_base64: str) -> Optional[np.ndarray]:
#         """
#         Decode a base64 data URL from canvas.toDataURL()
#         into a BGR NumPy frame for OpenCV.
#         """

#         try:
#             header_removed = image_base64.split(",", 1)[-1]
#             image_bytes = base64.b64decode(header_removed)

#             pil_image = Image.open(
#                 io.BytesIO(image_bytes)
#             ).convert("RGB")

#             return cv2.cvtColor(
#                 np.array(pil_image),
#                 cv2.COLOR_RGB2BGR,
#             )

#         except Exception:
#             return None