"""Simple test script with mocked Redis data."""

from robot_tui.app import RobotTUI
from robot_tui.redis_client import AsyncRedisClient


# Dummy object data
DUMMY_OBJECTS = {
    "Cup": (0.312, 0.156, 0.245),
    "Water Bottle": (0.421, 0.089, 0.312),
    "Phone": (0.156, 0.312, 0.178),
    "Remote": (0.534, 0.201, 0.095),
    "Pen": (0.289, 0.423, 0.134),
    "Notebook": (0.367, 0.298, 0.201),
    "Keyboard": (0.445, 0.167, 0.278),
    "Mouse": (0.198, 0.089, 0.156),
    "Headphones": (0.523, 0.334, 0.245),
    "Coffee Mug": (0.278, 0.245, 0.189),
    "Book": (0.401, 0.378, 0.223),
    "Tablet": (0.334, 0.134, 0.267),
    "Charger": (0.467, 0.289, 0.112),
    "Glasses": (0.156, 0.201, 0.145),
    "Watch": (0.389, 0.423, 0.167),
}

DUMMY_BOARD = (0.421, 0.156, 0.089)


class MockRedisClient(AsyncRedisClient):
    """Mock Redis client that returns dummy data."""

    async def connect(self) -> bool:
        self._connected = True
        if self._on_connect:
            self._on_connect()
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def get_objects(self) -> dict[str, tuple[float, float, float]]:
        return DUMMY_OBJECTS

    async def get_board_position(self) -> tuple[float, float, float] | None:
        return DUMMY_BOARD

    async def publish_command(self, command_json: str) -> bool:
        # Just print the command for testing
        print(f"[MOCK] Would publish: {command_json}")
        return True


class TestRobotTUI(RobotTUI):
    """Test version of RobotTUI with mocked Redis."""

    def __init__(self) -> None:
        super().__init__()
        # Replace with mock client
        self._redis = MockRedisClient(
            on_connect=self._on_redis_connect,
            on_disconnect=self._on_redis_disconnect,
        )


def main() -> None:
    """Run the test TUI."""
    app = TestRobotTUI()
    app.run()


if __name__ == "__main__":
    main()
