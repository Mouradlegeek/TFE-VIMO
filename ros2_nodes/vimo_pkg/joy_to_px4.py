#!/usr/bin/env python3
"""
Joy to PX4 — VIMO TFE ISIB 2025-2026
Joystick générique → setpoint attitude PX4 via MAVROS.
Validation axes, dead zone, limites sécurité.
"""

import rclpy
import numpy as np
from rclpy.node import Node
from sensor_msgs.msg import Joy

try:
    from mavros_msgs.msg import AttitudeTarget
    from geometry_msgs.msg import Quaternion
    HAS_MAVROS = True
except ImportError:
    HAS_MAVROS = False

DEAD_ZONE       = 0.05
MAX_ROLL_DEG    = 30.0
MAX_PITCH_DEG   = 30.0
MAX_YAW_RATE    = 1.0     # rad/s
MIN_AXES        = 6


def euler_to_quat(roll: float, pitch: float, yaw: float):
    cr, sr = np.cos(roll/2), np.sin(roll/2)
    cp, sp = np.cos(pitch/2), np.sin(pitch/2)
    cy, sy = np.cos(yaw/2), np.sin(yaw/2)
    return (
        cr*cp*cy + sr*sp*sy,
        sr*cp*cy - cr*sp*sy,
        cr*sp*cy + sr*cp*sy,
        cr*cp*sy - sr*sp*cy,
    )


class JoyToPx4Node(Node):

    def __init__(self):
        super().__init__('joy_to_px4')

        self._yaw = 0.0

        self.create_subscription(Joy, '/joy', self._cb_joy, 10)

        if HAS_MAVROS:
            self._pub = self.create_publisher(
                AttitudeTarget, '/mavros/setpoint_raw/attitude', 10)
        else:
            self._pub = None

        self.get_logger().info('[joy_to_px4] Démarré')

    def _cb_joy(self, msg: Joy):
        # Validation taille axes
        if len(msg.axes) < MIN_AXES:
            self.get_logger().warn(
                f'[joy_to_px4] Axes insuffisants: {len(msg.axes)} < {MIN_AXES}')
            return

        throttle = self._dz(msg.axes[1])
        roll_cmd = self._dz(msg.axes[3])
        pitch_cmd= self._dz(msg.axes[4])
        yaw_cmd  = self._dz(msg.axes[0])

        roll_rad  = np.deg2rad(roll_cmd  * MAX_ROLL_DEG)
        pitch_rad = np.deg2rad(pitch_cmd * MAX_PITCH_DEG)
        self._yaw += yaw_cmd * MAX_YAW_RATE * 0.02    # dt ≈ 50 Hz

        thrust = float(np.clip((throttle + 1.0) / 2.0, 0.0, 1.0))

        if self._pub is None:
            return

        qw, qx, qy, qz = euler_to_quat(roll_rad, pitch_rad, self._yaw)

        msg_out = AttitudeTarget()
        msg_out.header.stamp    = self.get_clock().now().to_msg()
        msg_out.type_mask       = AttitudeTarget.IGNORE_ROLL_RATE \
                                | AttitudeTarget.IGNORE_PITCH_RATE \
                                | AttitudeTarget.IGNORE_YAW_RATE
        msg_out.orientation.w   = float(qw)
        msg_out.orientation.x   = float(qx)
        msg_out.orientation.y   = float(qy)
        msg_out.orientation.z   = float(qz)
        msg_out.thrust          = thrust
        self._pub.publish(msg_out)

    @staticmethod
    def _dz(v: float) -> float:
        return 0.0 if abs(v) < DEAD_ZONE else float(v)


def main(args=None):
    rclpy.init(args=args)
    node = JoyToPx4Node()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
