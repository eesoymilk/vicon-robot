from robot_controller.robot_controller import RobotController

def main() -> None:
    controller = RobotController()
    controller.start()
    # controller.hard_coded_grasp()


if __name__ == "__main__":
    main()
