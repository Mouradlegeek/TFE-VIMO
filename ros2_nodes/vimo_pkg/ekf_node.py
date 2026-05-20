#!/usr/bin/env python3
"""
EKF Node adaptatif — VIMO TFE ISIB 2025-2026
État : [x, y, z, vx, vy, vz, qw, qx, qy, qz, bgx, bgy, bgz, bax, bay, baz]
Sources de mesure : VIO (OAK-D) + RPM odométrie + IMU
R adaptatif selon score qualité image Q
"""

import rclpy
import numpy as np
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import PoseStamped, TwistStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32MultiArray, Float32

# Paramètres EKF
DT_NOM       = 0.01          # 100 Hz nominal
ZUPT_THR     = 0.05          # m/s — seuil détection immobilité
OUTLIER_THR  = 0.40          # m   — rejet outlier position
BIAS_ALPHA   = 0.005         # EMA bias accel (BUG 2 corrigé)
POLE_COUNT   = 14
KV_MOTOR     = 920.0
V_NOM        = 16.0          # 4S nominal

# Paramètres bruit
Q_PROC_POS   = 1e-4
Q_PROC_VEL   = 1e-3
Q_PROC_Q     = 1e-5
Q_PROC_BG    = 1e-6
Q_PROC_BA    = 1e-6

R_VIO_BASE   = 0.05          # m²  — réduit si Q score élevé
R_RPM_BASE   = 0.10          # m/s²
R_ZUPT       = 1e-4          # m/s²


def quat_mult(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    ])


def quat_rotate(q, v):
    qv  = np.array([0.0, v[0], v[1], v[2]])
    qc  = np.array([q[0], -q[1], -q[2], -q[3]])
    tmp = quat_mult(q, qv)
    res = quat_mult(tmp, qc)
    return res[1:]


class EkfNode(Node):

    def __init__(self):
        super().__init__('ekf_node')

        # État [pos(3) vel(3) quat(4) bias_gyro(3) bias_accel(3)]
        self._x = np.zeros(16)
        self._x[6] = 1.0          # qw = 1 (identité)

        n = 16
        self._P = np.eye(n) * 0.01
        self._build_Q()

        self._last_imu_t  = None
        self._accel_bias  = np.zeros(3)
        self._bias_alpha  = BIAS_ALPHA
        self._q_score     = 1.0
        self._motor_rpm   = np.zeros(4)
        self._is_static   = False

        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.create_subscription(Imu,             '/mavros/imu/data',   self._cb_imu,    sensor_qos)
        self.create_subscription(PoseStamped,      '/vio/pose',          self._cb_vio,    10)
        self.create_subscription(Float32MultiArray,'/vimo/motor_rpm',    self._cb_rpm,    10)
        self.create_subscription(Float32,          '/vio/quality_score', self._cb_qscore, 10)

        self._pub_odom = self.create_publisher(Odometry,     '/vimo/odom',  10)
        self._pub_pose = self.create_publisher(PoseStamped,  '/vimo/pose',  10)

        self.get_logger().info('[ekf_node] Démarré')

    # ── Callbacks ──────────────────────────────────────────────────────────────

    def _cb_imu(self, msg: Imu):
        now = self.get_clock().now().nanoseconds * 1e-9
        if self._last_imu_t is None:
            self._last_imu_t = now
            return
        dt = min(now - self._last_imu_t, 0.1)
        self._last_imu_t = now

        accel = np.array([msg.linear_acceleration.x,
                          msg.linear_acceleration.y,
                          msg.linear_acceleration.z])
        gyro  = np.array([msg.angular_velocity.x,
                          msg.angular_velocity.y,
                          msg.angular_velocity.z])

        self._predict(accel, gyro, dt)
        self._detect_zupt(accel)
        self._publish_odom(msg.header.stamp)

    def _cb_vio(self, msg: PoseStamped):
        z_pos = np.array([msg.pose.position.x,
                          msg.pose.position.y,
                          msg.pose.position.z])
        z_quat = np.array([msg.pose.orientation.w,
                           msg.pose.orientation.x,
                           msg.pose.orientation.y,
                           msg.pose.orientation.z])

        # Rejet outlier
        pos_err = np.linalg.norm(z_pos - self._x[:3])
        if pos_err > OUTLIER_THR:
            self.get_logger().warn(f'[ekf_node] VIO outlier rejeté: {pos_err:.3f} m')
            return

        R_vio = (R_VIO_BASE / max(self._q_score, 0.1)) * np.eye(3)
        H     = np.zeros((3, 16))
        H[0, 0] = H[1, 1] = H[2, 2] = 1.0
        self._update(H, z_pos, self._x[:3], R_vio)

        # Mise à jour orientation
        self._x[6:10] = z_quat / np.linalg.norm(z_quat)

        # EMA bias accel — BUG 2 corrigé (pas d'intégration directe)
        pos_err_v = z_pos - self._x[:3]
        self._accel_bias = ((1 - self._bias_alpha) * self._accel_bias
                            + self._bias_alpha * pos_err_v)

    def _cb_rpm(self, msg: Float32MultiArray):
        self._motor_rpm = np.array(list(msg.data)[:4])
        # Vitesse estimée depuis RPM : v ≈ k * mean(RPM)
        rpm_mean = float(np.mean(self._motor_rpm))
        v_est    = rpm_mean / (KV_MOTOR * V_NOM) * 2.0   # normalisation empirique

        H    = np.zeros((1, 16))
        H[0, 3] = 1.0                                     # mesure sur vx
        R_rpm = np.array([[R_RPM_BASE / max(self._q_score, 0.1)]])
        self._update(H, np.array([v_est]), self._x[3:4], R_rpm)

    def _cb_qscore(self, msg: Float32):
        self._q_score = float(np.clip(msg.data, 0.05, 1.0))

    # ── EKF core ───────────────────────────────────────────────────────────────

    def _predict(self, accel, gyro, dt):
        x  = self._x
        q  = x[6:10]

        a_world = quat_rotate(q, accel - self._accel_bias) - np.array([0, 0, 9.81])

        x[:3]  += x[3:6] * dt + 0.5 * a_world * dt**2
        x[3:6] += a_world * dt

        dq = np.array([1.0,
                       0.5 * gyro[0] * dt,
                       0.5 * gyro[1] * dt,
                       0.5 * gyro[2] * dt])
        q_new = quat_mult(q, dq)
        x[6:10] = q_new / np.linalg.norm(q_new)

        F = np.eye(16)
        F[0, 3] = F[1, 4] = F[2, 5] = dt
        self._P = F @ self._P @ F.T + self._Q * dt

    def _update(self, H, z, z_hat, R):
        S  = H @ self._P @ H.T + R
        K  = self._P @ H.T @ np.linalg.inv(S)
        dz = z - z_hat
        self._x[:len(self._x)] += (K @ dz)[:len(self._x)]
        self._P = (np.eye(16) - K @ H) @ self._P

    def _detect_zupt(self, accel):
        accel_norm = np.linalg.norm(accel)
        self._is_static = abs(accel_norm - 9.81) < ZUPT_THR
        if self._is_static:
            H_zupt    = np.zeros((3, 16))
            H_zupt[0, 3] = H_zupt[1, 4] = H_zupt[2, 5] = 1.0
            R_zupt    = R_ZUPT * np.eye(3)
            self._update(H_zupt, np.zeros(3), self._x[3:6], R_zupt)

    def _build_Q(self):
        q = np.zeros(16)
        q[0:3]  = Q_PROC_POS
        q[3:6]  = Q_PROC_VEL
        q[6:10] = Q_PROC_Q
        q[10:13]= Q_PROC_BG
        q[13:16]= Q_PROC_BA
        self._Q = np.diag(q)

    def _publish_odom(self, stamp):
        msg = Odometry()
        msg.header.stamp    = stamp
        msg.header.frame_id = 'odom'
        msg.child_frame_id  = 'base_link'

        p = self._x
        msg.pose.pose.position.x    = float(p[0])
        msg.pose.pose.position.y    = float(p[1])
        msg.pose.pose.position.z    = float(p[2])
        msg.pose.pose.orientation.w = float(p[6])
        msg.pose.pose.orientation.x = float(p[7])
        msg.pose.pose.orientation.y = float(p[8])
        msg.pose.pose.orientation.z = float(p[9])

        msg.twist.twist.linear.x = float(p[3])
        msg.twist.twist.linear.y = float(p[4])
        msg.twist.twist.linear.z = float(p[5])

        self._pub_odom.publish(msg)

        pose_msg = PoseStamped()
        pose_msg.header = msg.header
        pose_msg.pose   = msg.pose.pose
        self._pub_pose.publish(pose_msg)


def main(args=None):
    rclpy.init(args=args)
    node = EkfNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
