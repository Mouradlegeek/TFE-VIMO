# Analyse Critique — TFE VIMO + Code Source

**Auteur : Mourad AARAB — ISIB 2025-2026**
**Date : 19 mai 2026**
**Projet : Localisation autonome de drone en environnement sans GPS (VIMO)**

---

## TABLE DES MATIERES

1. [Analyse du TFE (fond et forme)](#1-analyse-du-tfe)
2. [Analyse du code source](#2-analyse-du-code-source)
3. [Ameliorations prioritaires](#3-ameliorations-prioritaires)

---

## 1. ANALYSE DU TFE

### 1.1 Resume executif

| Aspect | Score | Commentaire |
|--------|-------|-------------|
| Contribution originale | 4/5 | EKF adaptatif legitime, parametres pas rigoureusement justifies |
| Rigueur mathematique | 4/5 | Excellente, certains choix ad-hoc |
| Validation experimentale | 3/5 | Au banc uniquement, pas de vol reel |
| Architecture logicielle | 5/5 | Modulaire, documentee, stable |
| Documentation | 4/5 | Pedagogique, liaisons aux cours ISIB excellentes |
| Qualite redactionnelle | 4/5 | Francais correct, figures de qualite |
| Honnetete scientifique | 5/5 | Admissions claires de limitations |

**Verdict : 16-18/20 apres corrections.**

### 1.2 Points forts

1. **EKF adaptatif comme contribution originale** : adapter R en fonction d'un score de qualite d'image en temps reel n'existait pas dans la litterature VIO.
2. **Architecture modulaire ROS2** : 12 noeuds independants, separation propre.
3. **Integration reelle documentee** : thermique, alimentation, EMI — les vrais problemes que personne ne documente.
4. **Honnetete scientifique** : admission claire que pas de vol reel, pas de boucle de fermeture.
5. **Pedagogie** : le chapitre 3 lie chaque concept aux cours ISIB.
6. **Stabilite** : 8 sessions rosbag sans fuite memoire, jusqu'a 1h45.

### 1.3 Problemes critiques (FOND)

#### P1. Score de qualite Q non justifie
- L'equation 6.3 : `Q = 0.30*L + 0.30*S + 0.25*D + 0.15*C` est presentee sans justification theorique.
- La section 2.4 mentionne une "etude de sensibilite" sans donnees ni graphiques.
- **Fix** : Ajouter une analyse de sensibilite detaillee (graphiques, tableaux) montrant comment Q varie si on change les poids. +2 pages.

#### P2. Parametres EKF empiriques non documentes
- lambda = 0.92 (velocity damping) : pas de justification.
- Q (matrice bruit de processus) : "reglee empiriquement" sans valeurs.
- Seuil rejet outliers 0.4 m : aucune justification.
- Tolerance sync 10 ms : aucune justification.
- **Fix** : Tableau explicite des valeurs avec justifications, meme empiriques. +1-2 pages.

#### P3. Pas de distinction test banc vs vol reel
- Le chapitre 7 melange les deux. Le score Q et les transitions de mode ne sont testes qu'au banc avec images injectees.
- **Fix** : Creer deux sous-sections explicites "Test banc" et "Vol reel (absent)". +0.5 page.

#### P4. Q_combined poids ad-hoc
- L'equation 2.1 : `Q_combined = 0.50*VIO + 0.35*RPM + 0.15*ESC_health` sans justification.
- **Fix** : Analyse de sensibilite. +1 page.

#### P5. Derive DR non contextualisee
- 3-4 cm en 30s : c'est bon ou mauvais ? Pas de comparaison avec d'autres IMU.
- **Fix** : Courbe theorique de derive sans damping, comparaison. +0.5 page.

### 1.4 Problemes importants (FORME)

#### F1. Conclusion trop personnelle
- Section 8.4 "mot de fin" : trop poetique ("quand j'ai commence ce projet..."). Pas dans un TFE scientifique.
- **Fix** : Garder 1 paragraphe, supprimer les histoires personnelles. -0.5 page.

#### F2. Chapitre 3 trop long
- 1 179 lignes qui couvrent physique + math. Pourrait etre scinde.
- **Fix** : Ok pour la soutenance, mais noter que c'est dense.

#### F3. Figures ameliorables
- Fig. 2.1 (concept general) : trop simple, ne montre pas la solution.
- Fig. 7.7 (courbes RPM) : 4 courbes trop rapprochees, ajouter un zoom.

#### F4. References
- Certaines references anciennes (Mahony 2012 = 14 ans).
- Certaines citations sans annee dans le texte.

### 1.5 Points mineurs
- Bande passante ICM-42688-P non mentionnee (800 Hz, on utilise 100 Hz).
- Formule precision profondeur stereo absente (seulement qualitative).
- Clock skew entre Pix32/UP4000/camera non verifie.

---

## 2. ANALYSE DU CODE SOURCE

### 2.1 Resume scoring

| Module | Qualite | Robustesse | Docs | Tests | Global |
|--------|---------|-----------|------|-------|--------|
| rpm_bridge_node | A | B+ | B | F | **B+** |
| ekf_node | A | A- | B | F | **A-** |
| vimo_sync_node | A | A | B | F | **A-** |
| dualsense_bridge | A- | B | B | F | **B+** |
| oakd_node | A | A- | B | F | **A** |
| launch scripts | A | A | B | F | **A-** |
| dataset_recorder | A | A | B | F | **A** |
| **GLOBAL** | **A-** | **B+** | **B** | **F** | **B+** |

### 2.2 Bugs critiques a corriger

#### BUG 1 — rpm_bridge_node.py ligne 252 : Division par zero
```python
# ACTUEL (CRASH si c_mean=0) :
c_max_dev = max(abs(c - c_mean) / c_mean for c in currents)

# CORRIGE :
if c_mean > 0.01:
    c_max_dev = max(abs(c - c_mean) / c_mean for c in currents)
else:
    c_max_dev = 0.0
```

#### BUG 2 — ekf_node.py ligne 365 : Integration directe au lieu d'EMA
```python
# ACTUEL (integration directe = diverge) :
self.accel_bias += self.bias_alpha * pos_err

# CORRIGE (EMA = converge) :
self.accel_bias = (1 - self.bias_alpha) * self.accel_bias + self.bias_alpha * pos_err
```

#### BUG 3 — dualsense_bridge.py : Exception silencieuse dans thread
Le thread joystick a un `except Exception: pass` qui masque les erreurs et peut causer une mort silencieuse du thread.

### 2.3 Problemes d'architecture

1. **Redondance esc_telemetry_node / rpm_bridge_node** : les deux publient `/drone/motor_alert`. Clarifier qui a la priorite.
2. **joy_to_px4.py** : pas de gestion d'erreurs, pas de dead zone, pas de validation taille axes.
3. **Pas de tests automatises** : zero test unitaire sur l'ensemble du workspace. C'est le point le plus faible.

### 2.4 Points forts du code

1. **rpm_bridge_node** : multi-source fallback impeccable (DShot > telemetry > sqrt throttle).
2. **ekf_node** : ZUPT logique, calibration statique, outlier rejection.
3. **oakd_node** : ancrage timestamp glissant = genial, backoff exponentiel pipeline.
4. **vimo_sync_node** : nearest-neighbor robuste, startup grace period.
5. **safety_monitor** : kill seulement si arme, debounce 5s FCU disconnect.
6. **Tous les noeuds** : ExternalShutdownException + rclpy.ok() = shutdown propre.

---

## 3. AMELIORATIONS PRIORITAIRES

### 3.1 Actions immediates (avant soutenance)

| # | Action | Fichier | Impact |
|---|--------|---------|--------|
| 1 | Fix division par zero c_mean | rpm_bridge_node.py:252 | Bug crash |
| 2 | Fix EMA bias (pas integration) | ekf_node.py:365 | Bug divergence |
| 3 | Justifier poids Q dans le TFE | chapters/06_ekf_adaptatif.tex | Rigueur |
| 4 | Documenter parametres empiriques | chapters/06 + annexe_B | Rigueur |
| 5 | Separer resultats banc/vol | chapters/07_resultats.tex | Clarte |
| 6 | Reduire "mot de fin" | chapters/08_conclusion.tex | Forme |

### 3.2 Actions moyen terme (si temps disponible)

| # | Action | Impact |
|---|--------|--------|
| 7 | Analyse sensibilite Q_combined | Rigueur |
| 8 | Fusionner esc_telemetry_node | Architecture |
| 9 | Ajouter tests unitaires mixer | Robustesse |
| 10 | Fix dualsense thread exception | Stabilite |
| 11 | Documenter EMA alpha/timeouts | Maintenabilite |
| 12 | Valider clock skew ROS2 | Rigueur |

### 3.3 Pour le jour du vol

| # | Action | Criticite |
|---|--------|-----------|
| A | **Activer Bidirectional DShot** via BLHeli32 Configurator (Windows) | BLOQUANT |
| B | Rebrancher cables TELEM1+TELEM2 | Important |
| C | Calibrer BATT1_V_DIV avec multimetre | Important |
| D | Test moteurs sol (helices enlevees) | Obligatoire |
| E | Premier hover 30s STABILIZED | Objectif |
