#!/usr/bin/env python3
"""
DualSense Bridge — VIMO TFE ISIB 2025-2026
Joystick DualSense → /mavros/manual_control
Thread protégé avec logging d'erreurs (BUG 3 corrigé — plus de except pass silencieux).
Dead zone configurable.
"""

import threading
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy

try:
    from mavros_msgs.msg import ManualControl
except ImportError:
    ManualControl = None

DEAD_ZONE = 0.05    # zone morte joystick
AXES_MIN  = 8       # nombre minimum d'axes attendus


def apply_dead_zone(value: float, threshold: float = DEAD_ZONE) -> float:
    return 0.0 if abs(value) < threshold else value


class DualsenseBridgeNode(Node):

    def __init__(self):
        super().__init__('dualsense_bridge')

        self._last_joy = None
        self._lock     = threading.Lock()

        self.create_subscription(Joy, '/joy', self._cb_joy, 10)

        if ManualControl is not None:
            self._pub_ctrl = self.create_publisher(ManualControl, '/mavros/manual_control', 10)
        else:
            self._pub_ctrl = None

        self._thread = threading.Thread(target=self._pub_loop, daemon=True)
        self._thread.start()

        self.get_logger().info('[dualsense_bridge] Démarré')

    def _cb_joy(self, msg: Joy):
        with self._lock:
            self._last_joy = msg

    def _pub_loop(self):
        rate = self.create_rate(50)
        while rclpy.ok():
            try:
                self._process()
                rate.sleep()
            except Exception as e:
                # BUG 3 corrigé — on log l'erreur au lieu de la masquer silencieusement
                self.get_logger().error(f'[dualsense_bridge] Erreur thread: {e}')

    def _process(self):
        with self._lock:
            joy = self._last_joy
        if joy is None or self._pub_ctrl is None:
            return

        # Validation taille axes (évite IndexError)
        if len(joy.axes) < AXES_MIN:
            self.get_logger().warn(
                f'[dualsense_bridge] Axes insuffisants: {len(joy.axes)} < {AXES_MIN}')
            return

        # Mapping DualSense → throttle/roll/pitch/yaw
        throttle = apply_dead_zone(joy.axes[1])   # stick gauche Y
        roll     = apply_dead_zone(joy.axes[3])   # stick droit X
        pitch    = apply_dead_zone(joy.axes[4])   # stick droit Y
        yaw      = apply_dead_zone(joy.axes[0])   # stick gauche X

        msg = ManualControl()
        msg.x = float(np.clip(pitch,    -1.0, 1.0) * 1000)
        msg.y = float(np.clip(roll,     -1.0, 1.0) * 1000)
        msg.z = float(np.clip((throttle + 1.0) / 2.0, 0.0, 1.0) * 1000)
        msg.r = float(np.clip(yaw,      -1.0, 1.0) * 1000)
        self._pub_ctrl.publish(msg)


import numpy as np   # noqa: E402 (import ici pour éviter erreur si numpy absent)


def main(args=None):
    rclpy.init(args=args)
    node = DualsenseBridgeNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
