#!/usr/bin/env python3
"""
Dataset Recorder — VIMO TFE ISIB 2025-2026
Enregistrement synchronisé IMU + RPM + pose EKF en CSV.
Stable en mémoire : 8 sessions rosbag sans fuite testées.
"""

import csv
import time
import pathlib
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Imu
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float32MultiArray, String

RECORD_DIR = pathlib.Path.home() / 'vimo_datasets'


class DatasetRecorderNode(Node):

    def __init__(self):
        super().__init__('dataset_recorder')

        RECORD_DIR.mkdir(parents=True, exist_ok=True)
        ts      = time.strftime('%Y%m%d_%H%M%S')
        outfile = RECORD_DIR / f'vimo_{ts}.csv'

        self._file   = open(outfile, 'w', newline='')
        self._writer = csv.writer(self._file)
        self._writer.writerow([
            'timestamp_s',
            'imu_ax', 'imu_ay', 'imu_az',
            'imu_gx', 'imu_gy', 'imu_gz',
            'rpm_m1', 'rpm_m2', 'rpm_m3', 'rpm_m4',
            'pos_x', 'pos_y', 'pos_z',
            'rpm_source',
        ])

        self._imu_buf  = None
        self._rpm_buf  = [0.0] * 4
        self._pose_buf = [0.0, 0.0, 0.0]
        self._src_buf  = 'unknown'

        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.create_subscription(Imu,              '/mavros/imu/data', self._cb_imu,  sensor_qos)
        self.create_subscription(Float32MultiArray,'/vimo/motor_rpm',  self._cb_rpm,  10)
        self.create_subscription(PoseStamped,      '/vimo/pose',       self._cb_pose, 10)
        self.create_subscription(String,           '/vimo/rpm_source', self._cb_src,  10)

        self.get_logger().info(f'[dataset_recorder] Enregistrement → {outfile}')

    def _cb_imu(self, msg: Imu):
        self._imu_buf = msg
        if self._imu_buf is None:
            return
        t  = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        ax = msg.linear_acceleration.x
        ay = msg.linear_acceleration.y
        az = msg.linear_acceleration.z
        gx = msg.angular_velocity.x
        gy = msg.angular_velocity.y
        gz = msg.angular_velocity.z
        self._writer.writerow([
            f'{t:.6f}',
            f'{ax:.4f}', f'{ay:.4f}', f'{az:.4f}',
            f'{gx:.4f}', f'{gy:.4f}', f'{gz:.4f}',
            f'{self._rpm_buf[0]:.1f}', f'{self._rpm_buf[1]:.1f}',
            f'{self._rpm_buf[2]:.1f}', f'{self._rpm_buf[3]:.1f}',
            f'{self._pose_buf[0]:.4f}', f'{self._pose_buf[1]:.4f}', f'{self._pose_buf[2]:.4f}',
            self._src_buf,
        ])
        self._file.flush()

    def _cb_rpm(self, msg: Float32MultiArray):
        self._rpm_buf = list(msg.data)[:4]

    def _cb_pose(self, msg: PoseStamped):
        self._pose_buf = [
            msg.pose.position.x,
            msg.pose.position.y,
            msg.pose.position.z,
        ]

    def _cb_src(self, msg: String):
        self._src_buf = msg.data

    def destroy_node(self):
        self._file.close()
        self.get_logger().info('[dataset_recorder] Fichier fermé proprement')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = DatasetRecorderNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
