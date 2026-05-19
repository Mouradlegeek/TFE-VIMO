# Prompt pour Claude Code — Session Windows BLHeli32

Copier-coller ce prompt dans Claude Code sur Windows pour etre guide pas-a-pas.

---

## Le Prompt

```
Tu es un assistant expert en configuration ESC drone. Je dois configurer mes 4 ESCs BLHeli32 (Flycolor X-Cross HV3) sur mon drone Holybro X500 V6 avec une FC Pix32 v6C sous PX4.

CONTEXTE :
- Les ESCs sont des BLHeli32 (ARM Cortex-M0, 32-bit)
- PX4 a deja DSHOT_BIDIR_EN=1 et MOT_POLE_COUNT=14 configures
- Le probleme : les ESCs n'ont pas "Bidirectional DShot" active dans leur firmware
- Resultat : /mavros/esc_status/status renvoie rpm=0 meme quand les moteurs tournent
- Le systeme utilise un fallback sqrt(throttle) pour estimer les RPM

OBJECTIF :
Guide-moi pas a pas pour :
1. Installer BLHeli32 Suite/Configurator sur Windows
2. Connecter aux ESCs via USB-C passthrough FC
3. Activer "Bidirectional DShot" sur les 4 ESCs
4. Desactiver le Beacon (bip agacant apres idle)
5. Flasher et verifier

CONTRAINTES SECURITE :
- HELICES TOUJOURS ENLEVEES pendant la config
- La batterie LiPo 4S doit etre branchee pour que les ESCs communiquent
- NE PAS ouvrir QGroundControl en meme temps que BLHeli32 Suite (conflit port COM)

PARAMETRES ESC A CONFIGURER :
- Bidirectional DShot : ON
- Motor Timing : Medium-High (23.4 deg)
- Beacon Delay : Infinite
- Beacon Strength : 0% ou Low
- Temperature Protection : 130C
- Motor Direction : Normal (sauf si inversion necessaire)

APRES LA CONFIG, je retournerai sur Linux pour verifier avec :
  bash ~/verify_blheli32.sh
  ros2 topic echo /mavros/esc_status/status

Si tu detectes un probleme ou si une etape echoue, propose des solutions alternatives.
Commence par me demander de confirmer que :
1. J'ai le cable USB-C branche au Pix32
2. La batterie est branchee
3. Les helices sont enlevees
4. QGroundControl est ferme
```

---

## Notes additionnelles

### Si BLHeli32 Suite ne detecte pas les ESCs :

Essayer ces commandes dans un terminal PowerShell pour identifier le port COM :

```powershell
# Lister les ports COM actifs
Get-WmiObject Win32_SerialPort | Select-Object DeviceID, Description
# OU
mode
```

### Si Passthrough echoue :

1. Dans QGroundControl (fermer ensuite), verifier :
   - Vehicle Setup > Parameters > `SYS_USE_IO = 0` (pas de IO board)
   - Reboot FC apres changement
2. Certaines FC necessitent un bootloader a jour pour le passthrough BLHeli32
3. Alternative : connecter les ESCs individuellement via un programmeur USB BLHeli32

### Versions compatibles :

| Outil | Version minimum |
|-------|----------------|
| BLHeli32 Suite | 32.9+ |
| BLHeli Configurator (Chrome) | 1.2.0+ |
| PX4 | v1.14+ (pour DShot passthrough) |
| Firmware ESC BLHeli32 | 32.7+ (pour bidir DShot) |
