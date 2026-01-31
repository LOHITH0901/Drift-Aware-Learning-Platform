from river import drift
import collections

class DriftDetector:
    def __init__(self):
        # We maintain a separate ADWIN instance for each student-topic pair
        # Key: (student_id, topic_id) -> ADWIN instance
        self.detectors = {}

    def get_detector(self, student_id: int, topic_id: int):
        key = (student_id, topic_id)
        if key not in self.detectors:
            self.detectors[key] = drift.ADWIN()
        return self.detectors[key]

    def update(self, student_id: int, topic_id: int, error: float) -> bool:
        """
        Updates the drift detector with the latest prediction error.
        Returns True if drift is detected.
        """
        detector = self.get_detector(student_id, topic_id)
        detector.update(error)
        return detector.drift_detected

    def reset_detector(self, student_id: int, topic_id: int):
        key = (student_id, topic_id)
        self.detectors[key] = drift.ADWIN()
