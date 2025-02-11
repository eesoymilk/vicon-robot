import pandas as pd
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
        print(f'Delta: ({    index_row[1]["X"] - df[hand_ref_marker]["X"][0]}, {    index_row[1]["Y"] - df[hand_ref_marker]["Y"][0]}, {    index_row[1]["Z"] - df[hand_ref_marker]["Z"][0]})')
        yield (
            (index_row[1]["X"] - df[hand_ref_marker]["X"][0]) / 1000 + init_pose[0],
            (index_row[1]["Y"] - df[hand_ref_marker]["Y"][0]) / 1000 + init_pose[1],
            (index_row[1]["Z"] - df[hand_ref_marker]["Z"][0]) / 1000 + init_pose[2]
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

    try:

        # time.sleep(0.2)
        # process_get_robot_current_status = GetRobotWaypointProcess()
        # process_get_robot_current_status.daemon = True
        # process_get_robot_current_status.start()
        # time.sleep(0.2)

        queue = Queue()

        p = Process(target=runWaypoint, args=(queue,))
        p.start()
        time.sleep(5)
        print("process started.")

        # 链接服务器
        #ip = 'localhost'
        ip = '192.168.0.246'
        port = 8899
        result = robot.connect(ip, port)

        if result != RobotErrorType.RobotError_SUCC:
            logger.info("connect server{0}:{1} failed.".format(ip, port))
        else:
            robot.enable_robot_event()
            robot.init_profile()
            # joint_maxvelc = (2.596177, 2.596177, 2.596177, 3.110177, 3.110177, 3.110177)
            joint_maxvelc = (20, 20, 20, 20, 20, 20)
            joint_maxacc = (17.308779/2.5, 17.308779/2.5, 17.308779/2.5, 17.308779/2.5, 17.308779/2.5, 17.308779/2.5)
            # joint_maxvelc = (0.596177, 0.596177, 0.596177, 1.110177, 1.110177, 1.110177)
            # joint_maxacc = (1.308779/2.5, 1.308779/2.5, 1.308779/2.5, 1.308779/2.5, 1.308779/2.5, 1.308779/2.5)
            robot.set_joint_maxacc(joint_maxacc)
            robot.set_joint_maxvelc(joint_maxvelc)
            # robot.set_arrival_ahead_time(0.5)
            # robot.set_arrival_ahead_blend(0.05) # try arrival ahead time (0.5)

            for x, y, z in list(get_hand_tracking_coords()):
                print(f"moving to ({x}, {y}, {z})")
                robot.move_to_target_in_cartesian((x, y, z), (179.99847, -0.000170, 84.27533))
            robot.disconnect()

            # while True:
            #     joint_radian = (0.541678, 0.225068, -0.948709, 0.397018, -1.570800, 0.541673)
            #     robot.move_joint(joint_radian, True)


            #     joint_radian = (55.5/180.0*pi, -20.5/180.0*pi, -72.5/180.0*pi, 38.5/180.0*pi, -90.5/180.0*pi, 55.5/180.0*pi)
            #     robot.move_joint(joint_radian, True)

            #     joint_radian = (0, 0, 0, 0, 0, 0)
            #     robot.move_joint(joint_radian, True)

            #     print("-----------------------------")

            #     queue.put(joint_radian)

            #     # time.sleep(5)

            #     # process_get_robot_current_status.test()

            #     # print("-----------------------------")

            #     # 断开服务器链接

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
