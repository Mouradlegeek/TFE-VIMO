# Configuration BLHeli32 ESC — Guide Windows pour VIMO X500 V6

## Contexte

Le drone VIMO X500 V6 utilise des ESCs **Flycolor X-Cross HV3 BLHeli32**. Le DShot bidirectionnel est configure cote PX4 (`DSHOT_BIDIR_EN=1`, `MOT_POLE_COUNT=14`), mais les ESCs eux-memes n'ont PAS encore "Bidirectional DSHOT" active dans leur firmware BLHeli32.

**Probleme actuel :** `/mavros/esc_status/status` renvoie `rpm=0` meme quand les moteurs tournent. Le systeme fonctionne en fallback `sqrt(throttle)`.

**Solution :** Utiliser BLHeli32 Configurator sur **Windows** pour activer le bidir DShot dans le firmware des 4 ESCs.

---

## Prerequis

1. **PC Windows** avec Chrome ou Edge
2. **Cable USB-C** connecte au Pix32 v6C (la FC fait passthrough vers les ESCs)
3. **Batterie LiPo 4S branchee** sur le drone (les ESCs ont besoin d'alimentation pour communiquer)
4. **HELICES ENLEVEES** (securite obligatoire)

---

## Etape 1 — Installer BLHeli32 Configurator

**Option A — Chrome App (recommandee) :**
1. Ouvrir Chrome sur Windows
2. Aller sur : `chrome://extensions/`
3. Activer "Mode developpeur" en haut a droite
4. Telecharger BLHeli32 Suite depuis : https://github.com/bitdump/BLHeli/tree/master/BLHeli_32%20ARM
5. OU utiliser la version desktop : https://github.com/blheli-configurator/blheli-configurator/releases

**Option B — BLHeli Suite (desktop) :**
1. Telecharger `BLHeliSuite32.zip` depuis le lien GitHub ci-dessus
2. Extraire et lancer `BLHeliSuite32.exe`

---

## Etape 2 — Connecter les ESCs via FC Passthrough

1. Brancher le cable USB-C du PC Windows vers le **Pix32 v6C**
2. Brancher la batterie LiPo sur le drone
3. **NE PAS** ouvrir QGroundControl (conflit port COM)
4. Dans BLHeli32 Configurator :
   - Selectionner le port COM du Pix32 (ex: COM3, COM4...)
   - Cliquer **"Connect"**
   - Selectionner **"BLHeli32 Passthrough"** comme interface
   - Cliquer **"Read Setup"**

5. Les 4 ESCs doivent apparaitre. Si non :
   - Verifier que la batterie est branchee
   - Essayer un autre port COM
   - Fermer QGC s'il est ouvert

---

## Etape 3 — Activer Bidirectional DShot

Pour **chaque ESC** (M1 a M4) :

1. Trouver le parametre **"Bidirectional DShot"** ou **"EDT (Extended DShot Telemetry)"**
2. Le mettre sur **"ON"** / **"Enabled"**
3. Verifier que **"Motor Direction"** est correct (Normal, sauf si moteur inverse)
4. Optionnel : Mettre **"Beacon Delay"** sur **"Infinite"** (desactive le bip agacant)
5. Optionnel : Mettre **"Beacon Strength"** sur **"0%"** ou desactiver

**Parametres recommandes pour VIMO :**

| Parametre | Valeur |
|-----------|--------|
| Bidirectional DShot | **ON** |
| Motor Timing | Medium-High (23.4 deg) |
| PWM Frequency | 48 kHz |
| Beacon Delay | Infinite |
| Beacon Strength | Low ou Off |
| Temperature Protection | 130 C |
| Low Voltage Protection | Off (gere par PX4) |
| Motor Direction | Normal (verifier sens rotation) |

6. Cliquer **"Write Setup"** pour flasher les 4 ESCs

---

## Etape 4 — Verification

Apres flash :

1. Debrancher USB, debrancher batterie
2. Attendre 5 secondes
3. Rebrancher batterie, rebrancher USB-C vers le PC **Linux**
4. Lancer le systeme :

```bash
# Sur le PC Linux
bash ~/VIMO_PROJECT/scripts/launch_full_dataset.sh --no-camera

# Dans un autre terminal
bash ~/verify_blheli32.sh
```

**Resultat attendu :**
- `/mavros/esc_status/status` : `rpm > 0` quand moteurs tournent
- `/drone/rpm_status` : `source: dshot_bidir` (plus fallback)
- `bidir_pkts` : compteur qui s'incremente

---

## Etape 5 — Test moteurs (HELICES ENLEVEES !)

```bash
bash ~/drone_ws/src/drone_bringup/scripts/test_motors_ground.sh
# Taper OUI → moteurs 15% pendant 8s
# Verifier rpm_diagnostic.py : RPM 1500-3000 attendus
```

---

## Troubleshooting

| Probleme | Solution |
|----------|----------|
| ESCs non detectes dans BLHeli32 Suite | Verifier batterie branchee, fermer QGC, essayer autre port COM |
| "Passthrough failed" | Reboot FC (debrancher/rebrancher USB), verifier firmware PX4 a jour |
| RPM toujours 0 apres flash | Verifier `DSHOT_BIDIR_EN=1` dans PX4 (QGC > Parameters) |
| Un seul ESC detecte | Verifier soudures signal DShot sur les 4 ESCs |
| ESC detecte mais pas de bidir option | Firmware ESC trop ancien, mettre a jour via BLHeli32 Suite > Flash |

---

## Parametres PX4 (deja configures)

Ces parametres sont deja actifs cote PX4 (verifier quand meme dans QGC) :

```
DSHOT_BIDIR_EN = 1          # Active bidir DShot cote FC
MOT_POLE_COUNT = 14         # 7 paires de poles (moteur 2216)
CBRK_IO_SAFETY = 22027      # Desactive safety switch
DSHOT_TEL_CFG  = 0          # Pas de telemetrie serie (on utilise bidir)
```

---

## Architecture RPM apres activation bidir

```
ESC BLHeli32 (bidir DShot)
    |
    v  (signal DShot retour)
Pix32 v6C (PX4)
    |
    v  (MAVLink ESC_STATUS msg)
MAVROS (/mavros/esc_status/status)
    |
    v  (ROS2 subscription)
rpm_bridge_node v3
    |
    +---> /drone/motor_rpm (Float32MultiArray @50Hz)
    +---> /drone/motor_rpm/M0..M3 (Float64 @50Hz)
    +---> /drone/rpm_avg (Float64 @50Hz)
    +---> /drone/rpm_status (JSON : source=dshot_bidir)
    +---> /drone/esc_health (JSON : voltage/current/temp)
```
