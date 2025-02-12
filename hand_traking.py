import pandas as pd
from vicon_stream import vicon_init, get_vicon_subject_markers
from utils.aubo_robot.robot_control import *

init_pose = (0.410444, 0.080962, 0.547597)
init_rot = (179.99847, -0.000170, 84.27533)


def get_hand_df() -> pd.DataFrame:
    df = pd.read_csv("hand_cal.csv", header=None)

    marker_row = df.iloc[0]
    axis_row = df.iloc[1]
    df = df.iloc[3:].reset_index(drop=True).apply(pd.to_numeric, errors="coerce")

    columns = [(marker, axis) for marker, axis in zip(marker_row, axis_row)]

    multi_index = pd.MultiIndex.from_tuples(columns, names=["Marker", "Axis"])
    df.columns = multi_index

    return df


def get_hand_tracking_coords():
    df = get_hand_df()

    hand_ref_marker = "Hand:Center"

    # delta = (
    #     df[hand_ref_marker]["X"][0] / 1000 - init_pose[0],
    #     df[hand_ref_marker]["Y"][0] / 1000 - init_pose[1],
    #     df[hand_ref_marker]["Z"][0] / 1000 - init_pose[2]
    # )

    for index_row in df[hand_ref_marker].iterrows():
        print(
            f"Delta: ({index_row[1]['X'] - df[hand_ref_marker]['X'][0]}, {index_row[1]['Y'] - df[hand_ref_marker]['Y'][0]}, {index_row[1]['Z'] - df[hand_ref_marker]['Z'][0]})"
        )
        yield (
            (index_row[1]["X"] - df[hand_ref_marker]["X"][0]) / 1000 + init_pose[0],
            (index_row[1]["Y"] - df[hand_ref_marker]["Y"][0]) / 1000 + init_pose[1],
            (index_row[1]["Z"] - df[hand_ref_marker]["Z"][0]) / 1000 + init_pose[2],
        )


def main():
    # 初始化logger
    logger_init()

    # 启动测试
    logger.info("{0} test beginning...".format(Auboi5Robot.get_local_time()))

    # 系统初始化
    Auboi5Robot.initialize()

    # 创建机械臂控制类
    robot = Auboi5Robot()

    # 创建上下文
    handle = robot.create_context()

    # 打印上下文
    logger.info("robot.rshd={0}".format(handle))

    vicon_client = vicon_init()

    try:
        # 链接服务器
        # ip = 'localhost'
        ip = "192.168.0.246"
        port = 8899
        result = robot.connect(ip, port)

        if result != RobotErrorType.RobotError_SUCC:
            logger.info("connect server{0}:{1} failed.".format(ip, port))
        else:
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

            vicon_client.GetFrame()
            base_markers = get_vicon_subject_markers(vicon_client, "Base")

            xy1 = base_markers["XYPlane1"][0]
            xy2 = base_markers["XYPlane2"][0]
            xy3 = base_markers["XYPlane3"][0]
            xy4 = base_markers["XYPlane4"][0]

            base_x = (xy1[0] + xy2[0] + xy3[0] + xy4[0]) / 4
            base_y = (xy1[1] + xy2[1] + xy3[1] + xy4[1]) / 4
            base_z = base_markers["Zbase"][0][2]
            flange_offset = 0.2

            robot.move_to_target_in_cartesian(init_pose, init_rot)

            while True:
                vicon_client.GetFrame()
                hand_markers = get_vicon_subject_markers(vicon_client, "Hand")
                target = hand_markers["Center"][0]
                if target[0] == 0  and target[1] == 0 and target[2] == 0:
                    continue

                target = (
                    (target[0] - base_x) / 1000,
                    (target[1] - base_y) / 1000,
                    ((target[2] - base_z) / 1000) + flange_offset
                )
                print(f"moving to {target}")

                delta = (target[0] - init_pose[0]), (target[1] - init_pose[1]), (target[2] - init_pose[2])
                print(f"delta {delta}")
                robot.move_to_target_in_cartesian(target, init_rot)


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
