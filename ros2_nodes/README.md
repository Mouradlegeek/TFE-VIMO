# VIMO ROS2 Nodes — TFE ISIB 2025-2026

**Mourad AARAB** — Localisation autonome de drone en environnement sans GPS  
Hardware : Holybro X500 V6 / Pix32 v6C / BLHeli32 / DShot600 / OAK-D

## Pipeline

```
OAK-D ──────── oakd_node ──────────────────────────────┐
                    │ /vio/pose  /vio/quality_score      │
PX4/MAVROS ─── rpm_bridge_node ── /vimo/motor_rpm ─── vimo_sync_node
                    │ /vimo/rpm_source                   │
                    │                                    ▼
IMU ──────────────────────────────────────────────── ekf_node ── /vimo/odom
                                                                     │
DualSense ── dualsense_bridge ── /mavros/manual_control           /vimo/pose
Joy ──────── joy_to_px4 ──────── /mavros/setpoint_raw/attitude
Safety ───── safety_monitor ──── /mavros/cmd/arming
Recorder ─── dataset_recorder ── ~/vimo_datasets/*.csv
```

## Noeuds

| Noeud | Topic(s) in | Topic(s) out | Description |
|-------|-------------|--------------|-------------|
| `rpm_bridge_node` | `/mavros/esc_status` | `/vimo/motor_rpm` `/vimo/rpm_source` | RPM DShot Bidir > Telem > sqrt fallback |
| `ekf_node` | `/mavros/imu/data` `/vio/pose` `/vimo/motor_rpm` | `/vimo/odom` `/vimo/pose` | EKF adaptatif ZUPT + outlier rejection |
| `vimo_sync_node` | `/mavros/imu/data` `/vimo/motor_rpm` | `/vimo/synced/imu` `/vimo/synced/rpm` | Sync nearest-neighbor |
| `safety_monitor` | `/mavros/state` `/vimo/kill` | `/safety/status` | Kill switch + debounce FCU |
| `oakd_node` | — | `/vio/pose` `/vio/quality_score` | OAK-D VIO + backoff exponentiel |
| `dualsense_bridge` | `/joy` | `/mavros/manual_control` | DualSense → MAVROS |
| `joy_to_px4` | `/joy` | `/mavros/setpoint_raw/attitude` | Joystick → attitude setpoint |
| `dataset_recorder` | multiples | CSV `~/vimo_datasets/` | Enregistrement sync |

## Installation

```bash
# Dans votre workspace ROS2 (ex: ~/vimo_ws)
mkdir -p ~/vimo_ws/src
cp -r ros2_nodes ~/vimo_ws/src/vimo_pkg
cd ~/vimo_ws
colcon build --packages-select vimo_pkg
source install/setup.bash
```

## Lancement

```bash
# MAVROS d'abord
ros2 launch mavros mavros.launch.py fcu_url:=/dev/ttyACM0:921600

# Puis le pipeline complet
ros2 launch vimo_pkg vimo_full.launch.py

# Vérifier la source RPM (doit afficher "DShot Bidir" si ESC configurés)
ros2 topic echo /vimo/rpm_source
```

## Paramètres hardware

| Paramètre PX4 | Valeur |
|---------------|--------|
| `DSHOT_BIDIR_EN` | 1 |
| `DSHOT_CONFIG` | 600 |
| `MOT_POLE_COUNT` | 14 |
| `CBRK_IO_SAFETY` | 22027 |
