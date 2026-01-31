"""Frame recorder for VLA data collection.

Listens to trajectory events from the robot controller via Redis and captures
synchronized camera frames during grab operations.

Usage:
    uv run robot-camera --device 0 --fps 10
"""

import argparse
import json
import logging
import time
from pathlib import Path

import cv2
import numpy as np

from robot_camera.camera import Camera
from robot_camera.redis_client import RedisSubscriber

logger = logging.getLogger(__name__)


class FrameRecorder:
    """Captures and saves camera frames synchronized with robot trajectories.

    Listens for trajectory events published by the robot controller's
    TrajectoryLogger, and captures frames at a configurable rate during
    active trajectory sessions.

    Output structure per session:
        {output_dir}/{session_id}_frames/
            000000.jpg
            000001.jpg
            ...
            metadata.jsonl   (one JSON line per frame)
    """

    PREVIEW_WINDOW = "Robot Camera"

    def __init__(
        self,
        camera: Camera,
        output_dir: Path,
        capture_fps: float = 10.0,
        jpeg_quality: int = 95,
        preview: bool = False,
    ) -> None:
        self.camera = camera
        self.output_dir = output_dir
        self.capture_interval = 1.0 / capture_fps
        self.capture_fps = capture_fps
        self.jpeg_quality = jpeg_quality
        self.preview = preview

        # Session state
        self._session_id: str | None = None
        self._session_dir: Path | None = None
        self._metadata_file = None
        self._frame_count: int = 0
        self._current_phase: str = ""
        self._current_gripper: int = 0

        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def recording(self) -> bool:
        return self._session_id is not None

    def start_session(self, session_id: str, event: dict) -> None:
        """Begin a new recording session."""
        self._session_id = session_id
        self._session_dir = self.output_dir / f"{session_id}_frames"
        self._session_dir.mkdir(parents=True, exist_ok=True)
        self._frame_count = 0
        self._current_phase = ""
        self._current_gripper = 0

        # Open metadata file for streaming writes
        self._metadata_file = open(self._session_dir / "metadata.jsonl", "w")

        logger.info(
            "Recording started: session=%s, dir=%s, fps=%.1f",
            session_id, self._session_dir, self.capture_fps,
        )

    def capture_frame(self) -> np.ndarray | None:
        """Capture one frame, save as JPEG, and append metadata.

        Returns:
            The captured frame in BGR format, or None if not recording.
        """
        if not self.recording or self._session_dir is None:
            return None

        timestamp = time.time()
        frame = self.camera.capture()

        filename = f"{self._frame_count:06d}.jpg"
        filepath = self._session_dir / filename

        # Convert RGB back to BGR for OpenCV imwrite
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite(
            str(filepath),
            bgr,
            [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality],
        )

        # Append metadata
        meta = {
            "frame_id": self._frame_count,
            "filename": filename,
            "timestamp": timestamp,
            "phase": self._current_phase,
            "gripper_position": self._current_gripper,
        }
        self._metadata_file.write(json.dumps(meta) + "\n")
        self._metadata_file.flush()

        self._frame_count += 1
        return bgr

    def end_session(self) -> None:
        """Finalize the recording session."""
        if not self.recording:
            return

        if self._metadata_file is not None:
            self._metadata_file.close()
            self._metadata_file = None

        logger.info(
            "Recording ended: session=%s, frames=%d",
            self._session_id, self._frame_count,
        )

        self._session_id = None
        self._session_dir = None
        self._frame_count = 0

    def handle_event(self, event: dict) -> None:
        """Handle a trajectory event from Redis."""
        event_type = event.get("event")

        if event_type == "start":
            session_id = event.get("session_id", "unknown")
            self.start_session(session_id, event)

        elif event_type == "phase":
            self._current_phase = event.get("phase", "")
            self._current_gripper = event.get("gripper_position", 0)

        elif event_type == "end":
            self.end_session()

    def show_preview(self, bgr: np.ndarray) -> None:
        """Show a frame in the preview window with status overlay."""
        display = bgr.copy()

        # Status text
        if self.recording:
            status = f"REC  #{self._frame_count:04d}  [{self._current_phase}]"
            color = (0, 0, 255)  # red
        else:
            status = "IDLE - waiting for trajectory"
            color = (0, 200, 0)  # green

        cv2.putText(display, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.imshow(self.PREVIEW_WINDOW, display)

    def run_capture_loop(self) -> None:
        """Capture frames at the configured FPS while a session is active.

        This runs in the main thread between Redis event checks.
        Call this repeatedly or in a tight loop.
        """
        if not self.recording:
            return

        bgr = self.capture_frame()
        if self.preview and bgr is not None:
            self.show_preview(bgr)
        time.sleep(self.capture_interval)


def main() -> None:
    """CLI entry point for the camera recorder."""
    parser = argparse.ArgumentParser(
        description="Record camera frames during robot trajectories for VLA training",
    )
    parser.add_argument("--device", type=int, default=0, help="Camera device ID")
    parser.add_argument("--width", type=int, default=640, help="Frame width")
    parser.add_argument("--height", type=int, default=480, help="Frame height")
    parser.add_argument("--fps", type=float, default=10.0, help="Capture frame rate")
    parser.add_argument("--quality", type=int, default=95, help="JPEG quality (0-100)")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "data" / "trajectories",
        help="Output directory (default: data/trajectories)",
    )
    parser.add_argument("--preview", action="store_true", help="Show live camera preview window")
    parser.add_argument("--redis-host", default="localhost", help="Redis host")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis port")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    camera = Camera(device_id=args.device, width=args.width, height=args.height)
    camera.open()

    recorder = FrameRecorder(
        camera=camera,
        output_dir=args.output_dir,
        capture_fps=args.fps,
        jpeg_quality=args.quality,
        preview=args.preview,
    )

    subscriber = RedisSubscriber(host=args.redis_host, port=args.redis_port)

    print(f"Camera recorder ready (device={args.device}, {args.width}x{args.height}, {args.fps}fps)")
    print(f"Output: {args.output_dir}")
    print("Waiting for trajectory events...")

    # We need to handle both:
    # 1. Redis events (start/phase/end) — to manage session lifecycle
    # 2. Frame capture at configured FPS — during active sessions
    #
    # Redis pubsub.listen() is blocking, so we use get_message() with a
    # timeout instead, interleaving it with frame capture.
    subscriber._pubsub.subscribe(subscriber.__class__.__name__)  # dummy to init
    subscriber._pubsub.unsubscribe()
    from robot_camera.redis_client import TRAJECTORY_EVENTS_CHANNEL
    subscriber._pubsub.subscribe(TRAJECTORY_EVENTS_CHANNEL)

    try:
        while True:
            # Check for Redis events (non-blocking)
            message = subscriber._pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=0.01,
            )
            if message and message["type"] == "message":
                try:
                    event = json.loads(message["data"])
                    recorder.handle_event(event)
                except (json.JSONDecodeError, KeyError):
                    logger.warning("Invalid event: %s", message.get("data"))

            # Capture frames if recording
            if recorder.recording:
                recorder.run_capture_loop()
            else:
                # Show live preview even when idle
                if args.preview:
                    frame = camera.capture()
                    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    recorder.show_preview(bgr)
                time.sleep(0.05)

            # Process OpenCV window events (needed for preview to stay responsive)
            if args.preview:
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    print("Preview quit requested")
                    break

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        recorder.end_session()
        camera.close()
        subscriber.close()
        if args.preview:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
