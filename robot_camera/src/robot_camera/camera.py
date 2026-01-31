"""Reusable camera capture class.

Use this for both data collection and VLA inference:

    from robot_camera import Camera

    with Camera(device_id=0) as cam:
        frame = cam.capture()  # (H, W, 3) uint8 RGB numpy array
"""

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class Camera:
    """USB camera capture via OpenCV.

    Provides a simple interface for capturing RGB frames from a USB camera.
    Designed to be reused across data collection and inference without changes.
    """

    def __init__(
        self,
        device_id: int = 0,
        width: int = 640,
        height: int = 480,
    ) -> None:
        self.device_id = device_id
        self.width = width
        self.height = height
        self._cap: cv2.VideoCapture | None = None

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def open(self) -> None:
        """Open the camera device."""
        if self.is_open:
            return
        self._cap = cv2.VideoCapture(self.device_id)
        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open camera device {self.device_id}")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(
            "Camera %d opened: requested %dx%d, actual %dx%d",
            self.device_id, self.width, self.height, actual_w, actual_h,
        )

    def close(self) -> None:
        """Release the camera device."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("Camera %d closed", self.device_id)

    def capture(self) -> np.ndarray:
        """Capture a single frame.

        Returns:
            RGB image as (H, W, 3) uint8 numpy array.

        Raises:
            RuntimeError: If camera is not open or frame capture fails.
        """
        if not self.is_open:
            raise RuntimeError("Camera is not open. Call open() first.")
        ret, frame = self._cap.read()
        if not ret:
            raise RuntimeError("Failed to capture frame")
        # OpenCV captures BGR, convert to RGB
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def __enter__(self) -> "Camera":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()
