import pyaubo_sdk
import time

robot_ip = "192.168.137.2"
robot_port = 8899
M_PI = 3.14159265358979323846
robot_rpc_client = pyaubo_sdk.RpcClient()

def exampleStartup():
    robot_name = robot_rpc_client.getRobotNames()[0]
    if 0 == robot_rpc_client.getRobotInterface(
            robot_name).getRobotManage().poweron():
        print("The robot is requesting power-on!")
        if 0 == robot_rpc_client.getRobotInterface(
                robot_name).getRobotManage().startup():
            print("The robot is requesting startup!")
            while 1:
                robot_mode = robot_rpc_client.getRobotInterface(robot_name) \
                    .getRobotState().getRobotModeType()
                print("Robot current mode: %s" % (robot_mode.name))
                if robot_mode == pyaubo_sdk.RobotModeType.Running:
                    break
                time.sleep(1)

def examplePoweroff():
    robot_name = robot_rpc_client.getRobotNames()[0]
    if 0 == robot_rpc_client.getRobotInterface(
            robot_name).getRobotManage().poweroff():
        print("The robot is requesting power-off!")

if __name__ == '__main__':
    robot_rpc_client.connect(robot_ip, robot_port)
    if robot_rpc_client.hasConnected():
        print("Robot rcp_client connected successfully!")
        robot_rpc_client.login("root", "1")
        if robot_rpc_client.hasLogined():
            print("Robot rcp_client logined successfully!")
            exampleStartup()
            examplePoweroff()
