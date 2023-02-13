#!/bin/python3

import sys
import time
import threading
from typing import List
import math
import rclpy
from tf2_ros.buffer_interface import TransformRegistration
from tf2_geometry_msgs import PointStamped, TransformStamped
from as2_python_api.drone_interface import DroneInterface

# pos= [[1,0,1],[-1,1,1.5],[-1,-1,2.0]]

speed = 1.0
ingore_yaw = True
height = 2.2
desp_gates = 0.5

drone_turn = 0

# gate_1_pose = PoseStamped()
# gate_2_pose = PoseStamped()

t_gate_0 = TransformStamped()
t_gate_1 = TransformStamped()

position_gate_0 = [0.0, 1.0]
position_gate_1 = [3.0, 1.0]

initial_pose_0 = [1.5, 0.0]
initial_pose_1 = [1.5, 2.0]

h_dist = math.sqrt((position_gate_0[0] - position_gate_1[0])
                   ** 2 + (position_gate_0[1] - position_gate_1[1])**2)

v_dist = math.sqrt((initial_pose_0[0] - initial_pose_1[0])
                   ** 2 + (initial_pose_0[1] - initial_pose_1[1])**2)

initial_point_rel_gate_0 = [h_dist/2,
                            -v_dist/2, 0.0]
print(initial_point_rel_gate_0)
initial_point_rel_gate_1 = [-h_dist/2,
                            v_dist/2, 0.0]
print(initial_point_rel_gate_1)
poses_rel_gate_0 = [[0.0, -desp_gates,
                     0.0], [0.0, desp_gates, 0.0]]
poses_rel_gate_1 = [[0.0, desp_gates,
                     0.0], [0.0, -desp_gates, 0.0]]

drones_ns = [
    'drone_sim_0',
    'drone_sim_1']
# drones_ns=['cf0','cf1']
# drones_ns=['cf1']

path_gate_0 = []
path_gate_1 = []


def gates_transforms():
    global t_gate_0, t_gate_1

    t_gate_0.header.frame_id = 'earth'
    t_gate_0.child_frame_id = 'gate_0'
    t_gate_0.transform.translation.x = position_gate_0[0]
    t_gate_0.transform.translation.y = position_gate_0[1]
    t_gate_0.transform.translation.z = 2.2
    t_gate_0.transform.rotation.x = 0.0
    t_gate_0.transform.rotation.y = 0.0
    t_gate_0.transform.rotation.z = 0.0
    t_gate_0.transform.rotation.w = 0.0

    t_gate_1.header.frame_id = 'earth'
    t_gate_1.child_frame_id = 'gate_1'
    t_gate_1.transform.translation.x = position_gate_1[0]
    t_gate_1.transform.translation.y = position_gate_1[1]
    t_gate_1.transform.translation.z = 2.2
    t_gate_1.transform.rotation.x = 0.0
    t_gate_1.transform.rotation.y = 0.0
    t_gate_1.transform.rotation.z = 0.0
    t_gate_1.transform.rotation.w = 0.0


def list_to_point(_l: list):
    ret = PointStamped()
    ret.point.x = _l[0]
    ret.point.y = _l[1]
    ret.point.z = _l[2]

    return ret


def point_to_list(point: PointStamped):
    ret = []
    ret.append(point.point.x)
    ret.append(point.point.y)
    ret.append(point.point.z)

    return ret


def transform_waypoints_from_gates_to_earth():

    registration = TransformRegistration()
    do_transform = registration.get(PointStamped)
    p0 = list_to_point(initial_point_rel_gate_0)
    p1 = list_to_point(initial_point_rel_gate_1)

    print(t_gate_0)
    print(t_gate_1)
    path_gate_0.append(point_to_list(do_transform(p0, t_gate_0)))
    path_gate_1.append(point_to_list(do_transform(p1, t_gate_1)))

    for point in poses_rel_gate_0:
        path_gate_0.append(point_to_list(
            do_transform(list_to_point(point), t_gate_0)))

    path_gate_0.append(point_to_list(do_transform(p1, t_gate_1)))

    for point in poses_rel_gate_1:
        path_gate_1.append(point_to_list(
            do_transform(list_to_point(point), t_gate_1)))

    path_gate_1.append(point_to_list(do_transform(p0, t_gate_0)))


def shutdown_all(uavs):
    print("Exiting...")
    for uav in uavs:
        uav.shutdown()
    sys.exit(1)

# create decorator for creating a thread for each drone


def takeoff(uav: DroneInterface):
    uav.arm()
    uav.offboard()
    uav.takeoff(2.0, 0.7)
    time.sleep(1)


def land(drone_interface: DroneInterface):
    drone_interface.land(0.4)


def follow_path(drone_interface: DroneInterface):
    path = []
    if drone_interface.drone_id == drones_ns[0]:
        if drone_turn == 0:
            path = path_gate_0
        else:
            path = path_gate_1
    elif drone_interface.drone_id == drones_ns[1]:
        if drone_turn == 0:
            path = path_gate_1
        else:
            path = path_gate_0
    print(path)
    print("path to follow")
    drone_interface.follow_path.follow_path_with_keep_yaw(
        path=path, speed=speed)
    # drone_interface.goto.go_to_point_path_facing(
    #     pose_generator(drone_interface), speed=speed)


def confirm(uavs: List[DroneInterface], msg: str = 'Continue') -> bool:
    confirmation = input(f"{msg}? (y/n): ")
    if confirmation == "y":
        return True
    elif confirmation == "n":
        return False
    else:
        shutdown_all(uavs)


def run_func(uavs: List[DroneInterface], func, *args):
    threads = []
    for uav in uavs:
        t = threading.Thread(target=func, args=(uav, *args))
        threads.append(t)
        t.start()
    print("Waiting for threads to finish...")
    for t in threads:
        t.join()
    print("all done")


def move_uavs(uavs):
    run_func(uavs, follow_path)
    return


def print_status(drone_interface: DroneInterface):
    while (True):
        drone_interface.get_logger().info(str(drone_interface.goto.status))


if __name__ == '__main__':

    rclpy.init()
    uavs = []
    for ns in drones_ns:
        uavs.append(DroneInterface(ns, verbose=False))

    print("Takeoff")
    confirm(uavs, "Takeoff")
    run_func(uavs, takeoff)
    print("Initial transformations")
    gates_transforms()
    transform_waypoints_from_gates_to_earth()
    print("Follow Path")
    confirm(uavs, "Follow Path")
    move_uavs(uavs)
    drone_turn = 1
    while confirm(uavs, "Replay"):
        move_uavs(uavs)
        drone_turn = abs(drone_turn) - 1

    print("Land")
    confirm(uavs, "Land")
    run_func(uavs, land)

    print("Shutdown")
    confirm(uavs, "Shutdown")
    rclpy.shutdown()

    exit(0)
