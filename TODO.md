# Roadmap d'amélioration de la logique de zoom

## Phase 1 : Corrections critiques ✅ TERMINÉE

### 1.1 Corriger l'incohérence `file_ratio == detected_ratio` ✅
- **Fait** : Logique clarifiée avec tolérance 16:9 conservée
- **Fait** : Test amélioré pour couvrir les deux cas (dans/hors tolérance)
- **Fichier** : `addon.py:334-337`, `tests/test_edge_cases.py:90-102`

### 1.2 Vérifier la validité mathématique du zoom combiné ✅
- **Fait** : 5 tests de validation mathématique créés
- **Fait** : Logs détaillés ajoutés (encoded_zoom, display_zoom, total_zoom)
- **Fait** : Formule `encoded_zoom × display_zoom` validée
- **Fichier** : `tests/test_zoom_math_validation.py`, `addon.py:339-376`

### 1.3 Améliorer le fallback pour zoom < 1.0 ✅
- **Fait** : Logs améliorés avec tous les paramètres (niveau ERROR)
- **Fait** : Fallback retourne 1.0 (pas de zoom) au lieu d'un zoom partiel
- **Fait** : Test ajouté pour vérifier la robustesse
- **Fichier** : `addon.py:373-381`, `tests/test_zoom_applier.py:137-175`

### 1.4 Restaurer la logique de détection des barres encodées ✅
- **Fait** : Logique corrigée pour utiliser file_ratio seulement si file OU content proche de 16:9
- **Fait** : Cas Invasion (file=240, content=178) fonctionne correctement (zoom 1.35)
- **Fait** : Cas Basil/Le Baron Rouge n'utilisent pas file_ratio incorrectement
- **Fichier** : `addon.py:610-632`, `tests/test_encoded_black_bars.py`

---

## Phase 2 : Refactoring partiel

### 2.1 Extraire la logique de décision de zoom
**Objectif** : Créer méthode `_should_skip_zoom(file_ratio, detected_ratio, tolerance_min, tolerance_max)`

**Actions** :
1. Créer méthode `_should_skip_zoom` dans `ZoomApplier`
2. Déplacer logique de `addon.py:334-339` et `385-387` dans cette méthode
3. Utiliser cette méthode dans `_calculate_zoom`
4. Ajouter tests unitaires pour `_should_skip_zoom`
5. Vérifier que tous les tests passent

**Fichiers** : Nouvelle méthode dans `ZoomApplier` classe, refactoriser `addon.py:312-399`

---

### 2.2 Séparer les calculs de zoom
**Objectif** : Créer méthodes distinctes pour encoded et display zoom

**Actions** :
1. Créer `_calculate_encoded_zoom(file_ratio, detected_ratio)` dans `ZoomApplier`
2. Créer `_calculate_display_zoom(detected_ratio, zoom_narrow_ratios)` dans `ZoomApplier`
3. Refactoriser `_calculate_zoom` pour utiliser ces méthodes
4. Ajouter tests unitaires pour chaque méthode
5. Vérifier que tous les tests passent

**Fichiers** : Refactoriser `addon.py:312-399`

---

### 2.3 Unifier l'accès à la tolérance 16:9
**Objectif** : Calculer tolérance une seule fois et passer explicitement

**Actions** :
1. Calculer tolérance une seule fois au début de `_calculate_zoom`
2. Passer explicitement aux méthodes qui en ont besoin
3. Vérifier que tous les tests passent

**Fichiers** : `addon.py:312-399`

---

## Phase 3 : Amélioration de la détection des barres encodées

### 3.1 Simplifier le seuil dynamique
**Objectif** : Remplacer `max(5, int(imdb_ratio * 0.05))` par constante ou calcul plus clair

**Actions** :
1. Remplacer seuil dynamique par constante ou calcul plus clair
2. Documenter le choix du seuil
3. Ajouter tests pour différents seuils
4. Vérifier que tous les tests passent

**Fichiers** : `addon.py:597`

---

### 3.2 Extraire la logique de détection
**Objectif** : Créer méthode `_detect_encoded_black_bars(imdb_ratio, file_ratio_temp, tolerance)`

**Actions** :
1. Créer méthode `_detect_encoded_black_bars` dans `Service`
2. Déplacer logique de `addon.py:593-621` dans cette méthode
3. Utiliser cette méthode dans `_detect_aspect_ratio`
4. Ajouter tests unitaires
5. Vérifier que tous les tests passent

**Fichiers** : Nouvelle méthode dans `Service` classe, refactoriser `addon.py:526-643`

---

## Phase 4 : Documentation

### 4.1 Créer `ZOOM_LOGIC.md`
**Objectif** : Documenter les règles métier

**Actions** :
1. Créer document expliquant :
   - Quand chaque chemin de zoom est pris
   - Pourquoi la multiplication des zooms
   - Cas limites et comportements attendus

**Fichier** : `ZOOM_LOGIC.md` (nouveau)

---

### 4.2 Ajouter tests de propriétés
**Objectif** : Vérifier propriétés mathématiques du zoom

**Actions** :
1. Créer `tests/test_zoom_properties.py`
2. Tests : `zoom >= 1.0` toujours, monotonie, cohérence

**Fichier** : `tests/test_zoom_properties.py` (nouveau)

---

### 4.3 Améliorer les logs
**Objectif** : Logs structurés pour faciliter le debugging

**Actions** :
1. Ajouter logs structurés dans `_calculate_zoom` (déjà fait partiellement)
2. Logger les chemins pris et valeurs intermédiaires (déjà fait)
3. Format structuré pour faciliter le debugging

**Fichiers** : `addon.py:312-399` (partiellement fait)

---

## Commandes de test

```bash
# Tests complets
pytest tests/ -v

# Tests spécifiques
pytest tests/test_zoom_applier.py -v
pytest tests/test_edge_cases.py -v
pytest tests/test_encoded_black_bars.py -v
pytest tests/test_zoom_math_validation.py -v

# Mode verbose pour debugging
pytest tests/ -vv --tb=long

# Avec couverture (si disponible)
pytest tests/ --cov=addon --cov-report=term-missing
```

---

## Statut global

- **Phase 1** : ✅ Terminée (4/4 tâches)
- **Phase 2** : ⏳ En attente (0/3 tâches)
- **Phase 3** : ⏳ En attente (0/2 tâches)
- **Phase 4** : ⏳ En attente (0/3 tâches)

**Progression totale** : 4/12 tâches (33%)

## Notes importantes

- **Logique de détection** : Utilise file_ratio si différence > threshold ET (file_ratio proche 16:9 OU content proche 16:9)
- **Cas validés** : Invasion (1.35), Basil (1.045), Le Baron Rouge (1.045), barres encodées réelles
- **Tests** : 67 tests passent
- **Prochaine étape** : Tests en conditions réelles pour valider > 80% de réussite

