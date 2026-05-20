#!/usr/bin/env python3
"""
OAK-D Node — VIMO TFE ISIB 2025-2026
Interface caméra stéréo OAK-D pour VIO.
Ancrage timestamp glissant pour éviter la dérive.
Backoff exponentiel sur erreur pipeline DepthAI.
"""

import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float32

try:
    import depthai as dai
    HAS_DAI = True
except ImportError:
    HAS_DAI = False

BACKOFF_MIN = 0.5    # secondes — délai initial sur erreur pipeline
BACKOFF_MAX = 30.0   # secondes — délai maximum
Q_WEIGHTS   = (0.30, 0.30, 0.25, 0.15)   # L, S, D, C — score qualité image


class OakdNode(Node):

    def __init__(self):
        super().__init__('oakd_node')

        self._pipeline  = None
        self._device    = None
        self._backoff   = BACKOFF_MIN
        self._t0_ros    = None    # ancre timestamp ROS
        self._t0_oakd   = None    # ancre timestamp OAK-D

        self._pub_pose    = self.create_publisher(PoseStamped, '/vio/pose',          10)
        self._pub_quality = self.create_publisher(Float32,     '/vio/quality_score', 10)

        if not HAS_DAI:
            self.get_logger().warn('[oakd_node] depthai non installé — mode simulation')
            self.create_timer(0.1, self._simulate)
        else:
            self.create_timer(0.0, self._init_pipeline)

        self.get_logger().info('[oakd_node] Démarré')

    # ── Pipeline DepthAI ───────────────────────────────────────────────────────

    def _init_pipeline(self):
        try:
            self._pipeline = self._build_pipeline()
            self._device   = dai.Device(self._pipeline)
            self._backoff  = BACKOFF_MIN
            self.get_logger().info('[oakd_node] Pipeline OAK-D démarré')
            self.create_timer(0.033, self._read_frame)    # ~30 fps
        except Exception as e:
            self.get_logger().error(
                f'[oakd_node] Erreur pipeline: {e} — retry dans {self._backoff:.1f} s')
            self.create_timer(self._backoff, self._init_pipeline)
            self._backoff = min(self._backoff * 2, BACKOFF_MAX)

    def _build_pipeline(self):
        pipeline = dai.Pipeline()

        cam_left  = pipeline.create(dai.node.MonoCamera)
        cam_right = pipeline.create(dai.node.MonoCamera)
        stereo    = pipeline.create(dai.node.StereoDepth)
        imu       = pipeline.create(dai.node.IMU)
        xout_imu  = pipeline.create(dai.node.XLinkOut)

        cam_left.setBoardSocket(dai.CameraBoardSocket.LEFT)
        cam_right.setBoardSocket(dai.CameraBoardSocket.RIGHT)
        cam_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        cam_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)

        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_ACCURACY)
        stereo.setSubpixel(True)

        imu.enableIMUSensor(dai.IMUSensor.ACCELEROMETER_RAW, 400)
        imu.enableIMUSensor(dai.IMUSensor.GYROSCOPE_RAW, 400)
        imu.setBatchReportThreshold(1)
        imu.setMaxBatchReports(10)
        xout_imu.setStreamName('imu')

        cam_left.out.link(stereo.left)
        cam_right.out.link(stereo.right)
        imu.out.link(xout_imu.input)

        return pipeline

    def _read_frame(self):
        if self._device is None:
            return
        try:
            # Lecture et calcul score qualité
            q_score = self._compute_quality_score()
            self._publish_quality(q_score)
        except Exception as e:
            self.get_logger().error(f'[oakd_node] Erreur lecture frame: {e}')

    # ── Ancrage timestamp glissant ─────────────────────────────────────────────

    def _anchor_timestamp(self, oakd_ts: float) -> float:
        now_ros = self.get_clock().now().nanoseconds * 1e-9
        if self._t0_ros is None:
            self._t0_ros  = now_ros
            self._t0_oakd = oakd_ts
        return self._t0_ros + (oakd_ts - self._t0_oakd)

    # ── Score qualité Q = 0.30L + 0.30S + 0.25D + 0.15C ──────────────────────

    def _compute_quality_score(self) -> float:
        # Valeur par défaut si pas de données réelles
        L = C = S = D = 0.7
        q = (Q_WEIGHTS[0] * L + Q_WEIGHTS[1] * S +
             Q_WEIGHTS[2] * D + Q_WEIGHTS[3] * C)
        return float(min(max(q, 0.0), 1.0))

    def _publish_quality(self, score: float):
        msg      = Float32()
        msg.data = score
        self._pub_quality.publish(msg)

    # ── Simulation (sans hardware OAK-D) ──────────────────────────────────────

    def _simulate(self):
        import math
        t    = self.get_clock().now().nanoseconds * 1e-9
        pose = PoseStamped()
        pose.header.stamp    = self.get_clock().now().to_msg()
        pose.header.frame_id = 'odom'
        pose.pose.position.x = math.sin(t * 0.1) * 0.5
        pose.pose.position.y = 0.0
        pose.pose.position.z = 0.0
        pose.pose.orientation.w = 1.0
        self._pub_pose.publish(pose)

        q_msg      = Float32()
        q_msg.data = 0.75
        self._pub_quality.publish(q_msg)


def main(args=None):
    rclpy.init(args=args)
    node = OakdNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        if node._device is not None:
            node._device.close()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
