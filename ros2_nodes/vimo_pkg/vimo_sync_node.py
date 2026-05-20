#!/usr/bin/env python3
"""
VIMO Sync Node — TFE ISIB 2025-2026
Synchronisation nearest-neighbor entre IMU, RPM et image caméra.
Grace period au démarrage pour laisser les topics s'initialiser.
"""

import rclpy
import numpy as np
from collections import deque
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32MultiArray

GRACE_S  = 3.0    # secondes avant de publier
WINDOW   = 50     # taille du buffer timestamps
MAX_LAG  = 0.05   # 50 ms de tolérance sync


class VimoSyncNode(Node):

    def __init__(self):
        super().__init__('vimo_sync_node')

        self._buf_imu = deque(maxlen=WINDOW)
        self._buf_rpm = deque(maxlen=WINDOW)
        self._start_t = self.get_clock().now().nanoseconds * 1e-9
        self._ready   = False

        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        self.create_subscription(Imu,              '/mavros/imu/data', self._cb_imu, sensor_qos)
        self.create_subscription(Float32MultiArray, '/vimo/motor_rpm', self._cb_rpm, 10)

        self._pub_imu = self.create_publisher(Imu,              '/vimo/synced/imu', 10)
        self._pub_rpm = self.create_publisher(Float32MultiArray,'/vimo/synced/rpm', 10)

        self.create_timer(0.01, self._tick)
        self.get_logger().info('[vimo_sync_node] Démarré — grace period 3 s')

    def _cb_imu(self, msg: Imu):
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        self._buf_imu.append((t, msg))

    def _cb_rpm(self, msg: Float32MultiArray):
        t = self.get_clock().now().nanoseconds * 1e-9
        self._buf_rpm.append((t, msg))

    def _tick(self):
        now = self.get_clock().now().nanoseconds * 1e-9

        if not self._ready:
            if now - self._start_t < GRACE_S:
                return
            self._ready = True
            self.get_logger().info('[vimo_sync_node] Grace period terminée — sync actif')

        if not self._buf_imu or not self._buf_rpm:
            return

        t_imu, imu_msg = self._buf_imu[-1]

        # Nearest-neighbor dans le buffer RPM
        best = min(self._buf_rpm, key=lambda x: abs(x[0] - t_imu))
        t_rpm, rpm_msg = best

        if abs(t_imu - t_rpm) > MAX_LAG:
            return

        self._pub_imu.publish(imu_msg)
        self._pub_rpm.publish(rpm_msg)


def main(args=None):
    rclpy.init(args=args)
    node = VimoSyncNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
