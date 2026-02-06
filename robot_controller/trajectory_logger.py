"""
Trajectory Logger for Robot Grab Operations

Records timestamped trajectory data during robot movements for model training.
Outputs CSV format with one row per timestep, suitable for sequence learning.

Uses async movement (issync=False) with tight polling loop for better sampling.
"""

import csv
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Robot states from AUBO SDK
ROBOT_STATE_STOPPED = 0
ROBOT_STATE_RUNNING = 1
ROBOT_STATE_PAUSED = 2


@dataclass
class WaypointSample:
    """A single timestamped waypoint sample during movement."""
    timestamp: float
    relative_time: float
    joint_angles: List[float]  # 6 joint angles in radians
    position: Tuple[float, float, float]  # (x, y, z) in meters
    orientation: Tuple[float, float, float, float]  # quaternion (w, x, y, z)
    robot_state: int  # 0=Stopped, 1=Running, 2=Paused
    phase: str
    gripper_position: int


@dataclass
class TrajectoryLog:
    """Complete trajectory log for a grab_object operation."""
    session_id: str
    object_name: Optional[str]
    target_position: Tuple[float, float, float]
    target_rotation: Tuple[float, float, float]
    return_position: Tuple[float, float, float]
    samples: List[WaypointSample] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None


class TrajectoryLogger:
    """
    Records robot trajectory data during grab operations.

    Uses synchronous polling during async robot movements for precise
    trajectory capture. Outputs CSV for ML training.
    """

    CSV_HEADER = [
        'session_id', 'object_name', 'phase', 'timestamp', 'relative_time',
        'j0', 'j1', 'j2', 'j3', 'j4', 'j5',
        'x', 'y', 'z',
        'qw', 'qx', 'qy', 'qz',
        'gripper', 'robot_state'
    ]

    EVENTS_CHANNEL = "trajectory_events"

    def __init__(
        self,
        robot,  # Auboi5Robot instance
        output_dir=None,  # type: Optional[Path]
        poll_rate_hz=50.0,  # type: float
        event_publisher=None,  # type: Optional[Callable[[str, str], None]]
    ):
        """
        Args:
            robot: Auboi5Robot instance with get_current_waypoint() method
            output_dir: Directory for saving trajectory logs
            poll_rate_hz: Polling frequency for waypoint sampling (default 50Hz)
            event_publisher: Optional callback(channel, json_str) for publishing
                trajectory events to Redis, used to synchronize external recorders
                (e.g. camera). Signature: event_publisher(channel: str, data: str)
        """
        self.robot = robot
        self.output_dir = output_dir or Path(__file__).parent / "trajectory_logs"
        self.poll_rate_hz = poll_rate_hz
        self.poll_interval = 1.0 / poll_rate_hz
        self._event_publisher = event_publisher

        # Current recording state
        self._current_log = None  # type: Optional[TrajectoryLog]
        self._current_phase = ""  # type: str
        self._start_time = 0.0  # type: float
        self._gripper_position = 0  # type: int

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("TrajectoryLogger initialized, output_dir=%s, poll_rate=%sHz", self.output_dir, poll_rate_hz)

    def _publish_event(self, event_data):
        # type: (dict) -> None
        """Publish a trajectory event via the configured publisher."""
        if self._event_publisher is not None:
            try:
                self._event_publisher(self.EVENTS_CHANNEL, json.dumps(event_data))
            except Exception:
                logger.warning("Failed to publish trajectory event", exc_info=True)

    def start_trajectory(
        self,
        target_position,  # type: Tuple[float, float, float]
        target_rotation,  # type: Tuple[float, float, float]
        return_position,  # type: Tuple[float, float, float]
        object_name=None,  # type: Optional[str]
    ):
        # type: (...) -> str
        """
        Begin recording a new trajectory.

        Returns:
            session_id: Unique identifier for this trajectory
        """
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self._start_time = time.time()

        self._current_log = TrajectoryLog(
            session_id=session_id,
            object_name=object_name,
            target_position=target_position,
            target_rotation=target_rotation,
            return_position=return_position,
        )

        self._publish_event({
            "event": "start",
            "session_id": session_id,
            "object_name": object_name,
            "target_position": list(target_position),
            "return_position": list(return_position),
            "timestamp": self._start_time,
        })

        logger.info("Started trajectory recording: %s, object=%s", session_id, object_name)
        return session_id

    def record_movement(
        self,
        joint_angles: List[float],
        phase_name: str,
        gripper_position: Optional[int] = None,
    ):
        """
        Execute a movement with async move_joint and record trajectory.

        This method:
        1. Starts async movement (issync=False)
        2. Polls get_current_waypoint() in a tight loop
        3. Stops when robot state returns to Stopped

        Args:
            joint_angles: Target joint angles for move_joint
            phase_name: Name of this movement phase
            gripper_position: Current gripper position (for logging)
        """
        if self._current_log is None:
            logger.warning("No active trajectory. Call start_trajectory first.")
            self.robot.move_joint(joint_angles, issync=True)
            return

        self._current_phase = phase_name
        if gripper_position is not None:
            self._gripper_position = gripper_position

        self._publish_event({
            "event": "phase",
            "session_id": self._current_log.session_id,
            "phase": phase_name,
            "gripper_position": self._gripper_position,
            "timestamp": time.time(),
        })

        logger.debug("Starting phase: %s", phase_name)

        # Sample initial position
        self._sample_waypoint()

        # Start async movement
        self.robot.move_joint(joint_angles, issync=False)

        # Small delay to let robot start moving
        time.sleep(0.05)

        # Poll until movement completes
        samples_in_phase = 0
        while True:
            self._sample_waypoint()
            samples_in_phase += 1

            robot_state = self.robot.get_robot_state()
            if robot_state == ROBOT_STATE_STOPPED:
                # Movement complete
                break

            time.sleep(self.poll_interval)

        # Final sample at end position
        self._sample_waypoint()

        logger.debug(f"Phase {phase_name} complete: {samples_in_phase} samples")
        self._current_phase = ""

    def end_trajectory(self, success: bool = True, error_message: str = None) -> Optional[Path]:
        """
        Finish recording and save the trajectory to CSV file.

        Returns:
            Path to the saved trajectory file
        """
        if self._current_log is None:
            logger.warning("No active trajectory to end.")
            return None

        self._current_log.success = success
        self._current_log.error_message = error_message

        self._publish_event({
            "event": "end",
            "session_id": self._current_log.session_id,
            "success": success,
            "timestamp": time.time(),
        })

        # Save to file
        output_path = self._save_trajectory_csv()

        total_samples = len(self._current_log.samples)
        duration = time.time() - self._start_time
        logger.info(
            f"Trajectory {self._current_log.session_id} saved: "
            f"{total_samples} samples, {duration:.2f}s, success={success}"
        )

        self._current_log = None
        return output_path

    def _sample_waypoint(self):
        """Take a single waypoint sample and add it to the current log."""
        if self._current_log is None or not self._current_phase:
            return

        waypoint = self.robot.get_current_waypoint()
        if waypoint is None:
            return

        robot_state = self.robot.get_robot_state()
        current_time = time.time()

        sample = WaypointSample(
            timestamp=current_time,
            relative_time=current_time - self._start_time,
            joint_angles=list(waypoint.get("joint", [0]*6)),
            position=tuple(waypoint.get("pos", (0, 0, 0))),
            orientation=tuple(waypoint.get("ori", (1, 0, 0, 0))),
            robot_state=robot_state if robot_state is not None else -1,
            phase=self._current_phase,
            gripper_position=self._gripper_position,
        )

        self._current_log.samples.append(sample)

    def _save_trajectory_csv(self) -> Path:
        """Save the trajectory samples to a CSV file."""
        filename = f"trajectory_{self._current_log.session_id}.csv"
        filepath = self.output_dir / filename

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(self.CSV_HEADER)

            for sample in self._current_log.samples:
                row = [
                    self._current_log.session_id,
                    self._current_log.object_name or "",
                    sample.phase,
                    f"{sample.timestamp:.6f}",
                    f"{sample.relative_time:.6f}",
                    *[f"{j:.6f}" for j in sample.joint_angles],
                    *[f"{p:.6f}" for p in sample.position],
                    *[f"{o:.6f}" for o in sample.orientation],
                    sample.gripper_position,
                    sample.robot_state,
                ]
                writer.writerow(row)

        return filepath
