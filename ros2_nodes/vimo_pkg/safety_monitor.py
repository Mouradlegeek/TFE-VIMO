#!/usr/bin/env python3
"""
Safety Monitor — VIMO TFE ISIB 2025-2026
Kill switch uniquement si armé.
Debounce 5 s sur déconnexion FCU pour éviter les faux positifs.
"""

import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
from std_srvs.srv import SetBool

try:
    from mavros_msgs.msg import State
    from mavros_msgs.srv import CommandBool
except ImportError:
    State = None
    CommandBool = None

DEBOUNCE_S   = 5.0    # secondes avant de déclarer FCU mort
HEARTBEAT_S  = 2.0    # timeout heartbeat MAVROS


class SafetyMonitorNode(Node):

    def __init__(self):
        super().__init__('safety_monitor')

        self._armed         = False
        self._fcu_ok        = True
        self._last_state_t  = time.monotonic()
        self._fcu_lost_t    = None

        if State is not None:
            self.create_subscription(State, '/mavros/state', self._cb_state, 10)

        self.create_subscription(Bool,   '/vimo/kill',       self._cb_kill,  10)
        self.create_subscription(String, '/drone/esc_alert', self._cb_alert, 10)

        self._pub_status = self.create_publisher(String, '/safety/status', 10)

        if CommandBool is not None:
            self._arm_cli = self.create_client(CommandBool, '/mavros/cmd/arming')

        self.create_timer(1.0, self._watchdog)
        self.get_logger().info('[safety_monitor] Démarré')

    def _cb_state(self, msg):
        self._armed        = msg.armed
        self._fcu_ok       = msg.connected
        self._last_state_t = time.monotonic()
        self._fcu_lost_t   = None

    def _cb_kill(self, msg: Bool):
        if msg.data:
            self._emergency_disarm('KILL topic reçu')

    def _cb_alert(self, msg: String):
        self.get_logger().warn(f'[safety_monitor] ALERTE ESC: {msg.data}')
        self._publish_status(f'ALERT:{msg.data}')

    def _watchdog(self):
        now = time.monotonic()

        # Détection perte FCU avec debounce
        if now - self._last_state_t > HEARTBEAT_S:
            if self._fcu_lost_t is None:
                self._fcu_lost_t = now
                self.get_logger().warn('[safety_monitor] FCU heartbeat perdu — debounce 5 s')
            elif now - self._fcu_lost_t > DEBOUNCE_S:
                if self._armed:
                    self._emergency_disarm('FCU déconnecté > 5 s')
        else:
            self._fcu_lost_t = None

        self._publish_status(f'armed={self._armed} fcu_ok={self._fcu_ok}')

    def _emergency_disarm(self, reason: str):
        if not self._armed:
            return
        self.get_logger().error(f'[safety_monitor] DISARM — {reason}')
        self._publish_status(f'DISARM:{reason}')

        if CommandBool is not None and self._arm_cli.service_is_ready():
            req = CommandBool.Request()
            req.value = False
            self._arm_cli.call_async(req)

    def _publish_status(self, text: str):
        msg      = String()
        msg.data = text
        self._pub_status.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SafetyMonitorNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
