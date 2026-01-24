"""Simple CLI for robot control - easier to debug than TUI."""

from .command import Command
from .redis_client import RedisClient


def main():
    redis = RedisClient()

    while True:
        print("\n" + "=" * 50)

        # Get objects
        objects = redis.get_objects()
        board_pos = redis.get_board_position()

        # Show board status
        if board_pos:
            print(f"Board: ({board_pos[0]:.3f}, {board_pos[1]:.3f}, {board_pos[2]:.3f})")
        else:
            print("Board: NOT DETECTED")

        print("-" * 50)

        # Show objects
        if not objects:
            print("No objects detected")
            input("Press Enter to refresh...")
            continue

        obj_list = list(objects.items())
        for i, (name, pos) in enumerate(obj_list):
            print(f"  [{i}] {name}: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")

        print("-" * 50)
        print("Commands: number to grab, r=refresh, q=quit")

        # Get input
        choice = input("> ").strip().lower()

        if choice == "q":
            print("Bye!")
            break
        elif choice == "r":
            continue
        elif choice.isdigit():
            idx = int(choice)
            if idx < 0 or idx >= len(obj_list):
                print(f"Invalid index: {idx}")
                continue

            if not board_pos:
                print("ERROR: Board not detected, cannot grab")
                continue

            name, pos = obj_list[idx]
            command = Command(
                function_name="grab_object",
                name=name,
                position=pos,
                inrange=True,
                return_position=board_pos,
            )

            json_cmd = command.model_dump_json()
            print(f"Sending: {json_cmd}")
            redis.publish_command(json_cmd)
            print(f"Sent grab command for {name}")
        else:
            print(f"Unknown command: {choice}")


if __name__ == "__main__":
    main()
