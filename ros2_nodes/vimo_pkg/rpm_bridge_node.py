#!/usr/bin/env python3
"""
RPM Bridge Node — VIMO TFE ISIB 2025-2026
Mourad AARAB — Holybro X500 V6 / Pix32 v6C / BLHeli32 / DShot600

Source prioritaire : DShot Bidirectionnel (/mavros/esc_status)
Fallback 1         : Télémétrie ESC     (/mavros/esc_telemetry)
Fallback 2         : Estimation sqrt(throttle) × KV × V_batt
"""

import time
import rclpy
import numpy as np
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from std_msgs.msg import Float32MultiArray, String
from sensor_msgs.msg import BatteryState

try:
    from mavros_msgs.msg import ESCStatus, ESCTelemetry, ActuatorOutputs
except ImportError:
    ESCStatus = ESCTelemetry = ActuatorOutputs = None

POLE_COUNT = 14       # Holybro 2216 KV920
KV_MOTOR   = 920.0    # RPM/V
TIMEOUT_S  = 0.5      # Basculement fallback si silence > 500 ms
PUB_HZ     = 50       # Fréquence de publication


class RpmBridgeNode(Node):

    def __init__(self):
        super().__init__('rpm_bridge_node')

        self._dshot_rpm    = [0.0] * 4
        self._telem_rpm    = [0.0] * 4
        self._throttle     = [0.0] * 4
        self._v_batt       = 16.0          # 4S nominal
        self._last_dshot_t = 0.0
        self._last_telem_t = 0.0
        self._source       = ''

        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        if ESCStatus is not None:
            self.create_subscription(ESCStatus,    '/mavros/esc_status',
                                     self._cb_dshot,    sensor_qos)
            self.create_subscription(ESCTelemetry, '/mavros/esc_telemetry',
                                     self._cb_telemetry, sensor_qos)
            self.create_subscription(ActuatorOutputs, '/mavros/actuator_outputs',
                                     self._cb_actuator,  sensor_qos)

        self.create_subscription(BatteryState, '/mavros/battery',
                                 self._cb_battery, sensor_qos)

        self._pub_rpm   = self.create_publisher(Float32MultiArray, '/vimo/motor_rpm',   10)
        self._pub_alert = self.create_publisher(String,            '/drone/esc_alert',  10)
        self._pub_src   = self.create_publisher(String,            '/vimo/rpm_source',  10)

        self.create_timer(1.0 / PUB_HZ, self._publish)
        self.get_logger().info('[rpm_bridge_node] Démarré — attente données ESC...')

    # ── Callbacks ──────────────────────────────────────────────────────────────

    def _cb_dshot(self, msg):
        now = time.monotonic()
        rpms     = []
        currents = []
        for esc in list(msg.esc_status)[:4]:
            rpms.append(float(esc.rpm))
            currents.append(float(esc.current))

        self._dshot_rpm    = rpms
        self._last_dshot_t = now

        # Détection déséquilibre courant — BUG 1 corrigé (division par zéro)
        c_mean = sum(currents) / max(len(currents), 1)
        if c_mean > 0.01:
            c_max_dev = max(abs(c - c_mean) / c_mean for c in currents)
            if c_max_dev > 0.30:
                self._publish_alert(f'ESC_IMBALANCE: déviation courant {c_max_dev:.1%}')
        else:
            c_max_dev = 0.0

    def _cb_telemetry(self, msg):
        self._telem_rpm    = [float(i.rpm) / (POLE_COUNT / 2)
                              for i in list(msg.esc_telemetry)[:4]]
        self._last_telem_t = time.monotonic()

    def _cb_actuator(self, msg):
        self._throttle = [max(0.0, min(1.0, float(o)))
                          for o in list(msg.output)[:4]]

    def _cb_battery(self, msg):
        if msg.voltage > 10.0:
            self._v_batt = float(msg.voltage)

    # ── Publication ────────────────────────────────────────────────────────────

    def _publish(self):
        now = time.monotonic()
        rpms, source = self._select_source(now)

        if source != self._source:
            self._source = source
            self.get_logger().info(f'[rpm_bridge_node] Source RPM → [{source}]')

        rpm_msg      = Float32MultiArray()
        rpm_msg.data = [float(r) for r in rpms]
        self._pub_rpm.publish(rpm_msg)

        src_msg      = String()
        src_msg.data = source
        self._pub_src.publish(src_msg)

    def _select_source(self, now: float):
        if now - self._last_dshot_t < TIMEOUT_S and any(r > 0 for r in self._dshot_rpm):
            return self._dshot_rpm, 'DShot Bidir'
        if now - self._last_telem_t < TIMEOUT_S and any(r > 0 for r in self._telem_rpm):
            return self._telem_rpm, 'Telemetry'
        rpms = [np.sqrt(t) * KV_MOTOR * self._v_batt for t in self._throttle]
        return rpms, 'Fallback sqrt'

    def _publish_alert(self, text: str):
        msg      = String()
        msg.data = text
        self._pub_alert.publish(msg)
        self.get_logger().warn(f'[rpm_bridge_node] ALERTE: {text}')


def main(args=None):
    rclpy.init(args=args)
    node = RpmBridgeNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
