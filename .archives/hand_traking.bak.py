import logging

import numpy as np
from vicon.vicon_client import ViconClient
from aubo_robot.auboi5_robot import (
    Auboi5Robot,
    RobotError,
    RobotErrorType,
    logger_init,
)

ROBOT_INIT_POSE = (0.410444, 0.080962, 0.547597)
ROBOT_INIT_ROT = (179.99847, -0.000170, 84.27533)
ROBOT_IP = "192.168.0.246"
ROBOT_PORT = 8899

logger = logging.getLogger("main.hand_tracking")


def convert_vicon_to_robot_coords(vicon_coords):
    return vicon_coords / 1000


def main():
    logger_init()
    logger.info(f"{Auboi5Robot.get_local_time()} test beginning...")

    # 系统初始化
    Auboi5Robot.initialize()

    # 创建机械臂控制类
    robot = Auboi5Robot()

    # 创建上下文
    handle = robot.create_context()

    # 打印上下文
    logger.info(f"robot.rshd={handle}")

    # Initialize Vicon Client
    vicon_client = ViconClient()

    try:
        # Connect to the robot
        result = robot.connect(ROBOT_IP, ROBOT_PORT)

        if result != RobotErrorType.RobotError_SUCC:
            raise RobotError(
                result, error_msg=f"connect server{ROBOT_IP}:{ROBOT_PORT} failed."
            )

        robot.enable_robot_event()
        robot.init_profile()
        joint_maxvelc = (20, 20, 20, 20, 20, 20)
        joint_maxacc = (
            17.308779 / 2.5,
            17.308779 / 2.5,
            17.308779 / 2.5,
            17.308779 / 2.5,
            17.308779 / 2.5,
            17.308779 / 2.5,
        )
        robot.set_joint_maxacc(joint_maxacc)
        robot.set_joint_maxvelc(joint_maxvelc)
        # robot.set_arrival_ahead_time(0.5)
        # robot.set_arrival_ahead_blend(0.05) # try arrival ahead time (0.5)

        vicon_client.get_frame()
        base_markers = vicon_client.get_vicon_subject_markers("Base")

        robot_base_xy1 = np.array(base_markers["XYPlane1"][0])
        robot_base_xy2 = np.array(base_markers["XYPlane2"][0])
        robot_base_xy3 = np.array(base_markers["XYPlane3"][0])
        robot_base_xy4 = np.array(base_markers["XYPlane4"][0])

        robot_base = (
            robot_base_xy1 + robot_base_xy2 + robot_base_xy3 + robot_base_xy4
        ) / 4

        robot_base[2] = base_markers["Zbase"][0][2]

        # xy1 = base_markers["XYPlane1"][0]
        # xy2 = base_markers["XYPlane2"][0]
        # xy3 = base_markers["XYPlane3"][0]
        # xy4 = base_markers["XYPlane4"][0]

        # base_x = (xy1[0] + xy2[0] + xy3[0] + xy4[0]) / 4
        # base_y = (xy1[1] + xy2[1] + xy3[1] + xy4[1]) / 4
        # base_z = base_markers["Zbase"][0][2]
        flange_offset = 0.2

        robot.move_to_target_in_cartesian(ROBOT_INIT_POSE, ROBOT_INIT_ROT)

        while True:
            vicon_client.get_frame()
            hand_markers = vicon_client.get_vicon_subject_markers("Hand")
            target = np.array(hand_markers["Center"][0]) / 1000
            if target[0] == 0 and target[1] == 0 and target[2] == 0:
                continue

            # target = (
            #     (target[0] - base_x) / 1000,
            #     (target[1] - base_y) / 1000,
            #     ((target[2] - base_z) / 1000) + flange_offset,
            # )
            print(f"moving to {target}")

            delta = target - np.array(ROBOT_INIT_POSE)
            # delta = (
            #     (target[0] - ROBOT_INIT_POSE[0]),
            #     (target[1] - ROBOT_INIT_POSE[1]),
            #     (target[2] - ROBOT_INIT_POSE[2]),
            # )
            print(f"delta {delta}")
            robot.move_to_target_in_cartesian(target, ROBOT_INIT_ROT)

    except KeyboardInterrupt:
        robot.move_stop()

    except RobotError as e:
        logger.error("robot Event:{0}".format(e))

    # 断开服务器链接
    if robot.connected:
        # 断开机械臂链接
        robot.disconnect()
    # 释放库资源
    Auboi5Robot.uninitialize()
    print("run end-------------------------")


if __name__ == "__main__":
    main()
