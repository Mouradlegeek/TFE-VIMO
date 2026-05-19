# Prompt pour Claude — Session Ubuntu (recompilation PX4)

## Contexte à donner à Claude au début de la session Ubuntu

```
Je travaille sur mon TFE VIMO (drone GPS-denied, ISIB Bruxelles).
Je dois recompiler PX4 v1.15 pour le Pix32 v6C (px4_fmu-v6c) afin d'inclure
le module BLHeli passthrough (CONFIG_DRIVERS_BLHELI=y).

Le module blheli n'est pas dans le firmware standard — vérifié via NSH le 19/05/2026.
Le but est de pouvoir ensuite utiliser BLHeliSuite32 (Windows) pour activer
Bidirectional DShot = ON sur les 4 ESC Flycolor X-Cross HV3 BLHeli32.

Hardware :
- FC : Holybro Pix32 v6C (STM32H743, board target : px4_fmu-v6c)
- ESC : Flycolor X-Cross HV3 4-en-1, firmware BLHeli32
- Moteurs : Holybro 2216 KV920, 14 pôles

Le script de build est dans mon repo GitHub :
https://github.com/Mouradlegeek/TFE-VIMO/blob/master/blheli32_windows_guide/build_px4_blheli.sh

Lance : bash build_px4_blheli.sh

Après le build :
- Copier le .px4 sur Windows
- Flasher via QGC (Vehicle Setup → Firmware → Custom)
- Utiliser BLHeliSuite32 sur COM3 avec interface "SiLabs BLHeli32 Bootloader (Betaflight/Cleanflight)"
- BLHeliSuite32 est déjà installé : C:\Users\aarab\Desktop\BLHeliSuite32\BLHeliSuite32.exe

Paramètres PX4 à vérifier/restaurer après flash :
- DSHOT_BIDIR_EN = 1
- DSHOT_CONFIG = 600
- MOT_POLE_COUNT = 14
- CBRK_IO_SAFETY = 22027
```

## Vérification rapide avant de lancer le build

```bash
# Vérifier que l'environnement PX4 est fonctionnel
arm-none-eabi-gcc --version
python3 --version
cmake --version

# Si PX4 déjà cloné, vérifier la branche
cd ~/PX4-Autopilot && git branch
```

## Commande directe

```bash
cd ~
curl -O https://raw.githubusercontent.com/Mouradlegeek/TFE-VIMO/master/blheli32_windows_guide/build_px4_blheli.sh
bash build_px4_blheli.sh
```

## Après le flash — test BLHeli sur Windows

1. Brancher batterie LiPo 4S + USB-C Pix32 sur le PC Windows
2. Ouvrir QGC → MAVLink Console → taper `blheli` (doit répondre maintenant)
3. Fermer QGC
4. Ouvrir BLHeliSuite32.exe
5. Interface : SiLabs BLHeli32 Bootloader (Betaflight / Cleanflight)
6. COM3, 115200 → Connect → Read Setup
7. Pour chaque ESC : Bidirectional DShot = ON, Motor Timing = Medium-High, PWM Freq = 48kHz
8. Write Setup → Read Setup (vérifier)

## Vérification finale Ubuntu (après config ESC)

```bash
ros2 launch mavros mavros.launch.py fcu_url:=/dev/ttyACM0:921600
ros2 topic echo /mavros/esc_status
# RPM non-zéro quand moteurs tournent = succès
# rpm_bridge_node doit afficher [DShot Bidir] au lieu de [Fallback sqrt]
```
