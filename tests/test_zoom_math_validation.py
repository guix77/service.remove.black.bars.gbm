"""
Tests de validation mathématique pour le calcul de zoom combiné.
Vérifie que la formule encoded_zoom × display_zoom est mathématiquement correcte.
"""
import sys
import os
import pytest

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mocker les modules Kodi
import tests.mock_kodi as mock_kodi
mock_xbmc = mock_kodi.MockXbmc()
sys.modules['xbmc'] = mock_xbmc
sys.modules['xbmcaddon'] = type(sys)('xbmcaddon')
sys.modules['xbmcaddon'].Addon = lambda: mock_kodi.MockAddon()
sys.modules['xbmcgui'] = mock_kodi.MockXbmcgui()

from addon import ZoomApplier


@pytest.fixture
def zoom():
    """Fixture pour créer un ZoomApplier"""
    return ZoomApplier()


def test_combined_zoom_horizontal_encoded_bars(zoom):
    """
    Test validation mathématique : barres encodées horizontales + barres affichage
    
    Cas : file=240 (2.40:1), content=235 (2.35:1), screen=177 (16:9)
    
    Calcul manuel :
    1. Barres encodées horizontales : file est plus large que content
       - encoded_zoom = file_ratio / detected_ratio = 240 / 235 = 1.0213
       - Zoom pour enlever les barres encodées horizontales
    
    2. Barres affichage : content (235) > screen (177)
       - display_zoom = detected_ratio / 177 = 235 / 177 = 1.3277
       - Zoom pour enlever les barres affichage
    
    3. Zoom total : encoded_zoom × display_zoom = 1.0213 × 1.3277 = 1.356
    
    Vérification : Le zoom total doit être le produit des deux zooms
    """
    file_ratio = 240
    detected_ratio = 235
    
    # Calcul manuel
    encoded_zoom_manual = file_ratio / float(detected_ratio)  # 240 / 235
    display_zoom_manual = detected_ratio / 177.0  # 235 / 177
    expected_total_manual = encoded_zoom_manual * display_zoom_manual
    
    # Calcul par le code
    zoom_value = zoom._calculate_zoom(detected_ratio, file_ratio=file_ratio)
    
    # Vérification
    assert abs(zoom_value - expected_total_manual) < 0.001, \
        f"Zoom combiné incorrect: attendu {expected_total_manual:.4f}, obtenu {zoom_value:.4f}"
    assert zoom_value > 1.0, "Zoom doit être > 1.0 pour enlever les barres"
    
    # Vérification que le zoom est raisonnable (pas trop élevé)
    assert zoom_value < 2.0, f"Zoom {zoom_value:.4f} semble trop élevé"


def test_combined_zoom_vertical_encoded_bars(zoom):
    """
    Test validation mathématique : barres encodées verticales + barres affichage
    
    Cas : file=175 (16:9), content=185 (1.85:1), screen=177 (16:9)
    
    Calcul manuel :
    1. Barres encodées verticales : file est plus étroit que content
       - encoded_zoom = detected_ratio / file_ratio = 185 / 175 = 1.0571
       - Zoom pour enlever les barres encodées verticales
    
    2. Barres affichage : content (185) > screen (177)
       - display_zoom = detected_ratio / 177 = 185 / 177 = 1.0452
       - Zoom pour enlever les barres affichage
    
    3. Zoom total : encoded_zoom × display_zoom = 1.0571 × 1.0452 = 1.105
    
    Vérification : Le zoom total doit être le produit des deux zooms
    """
    file_ratio = 175
    detected_ratio = 185
    
    # Calcul manuel
    encoded_zoom_manual = detected_ratio / float(file_ratio)  # 185 / 175
    display_zoom_manual = detected_ratio / 177.0  # 185 / 177
    expected_total_manual = encoded_zoom_manual * display_zoom_manual
    
    # Calcul par le code
    zoom_value = zoom._calculate_zoom(detected_ratio, file_ratio=file_ratio)
    
    # Vérification
    assert abs(zoom_value - expected_total_manual) < 0.001, \
        f"Zoom combiné incorrect: attendu {expected_total_manual:.4f}, obtenu {zoom_value:.4f}"
    assert zoom_value > 1.0, "Zoom doit être > 1.0 pour enlever les barres"


def test_encoded_bars_only_no_display_bars(zoom):
    """
    Test : barres encodées uniquement, pas de barres affichage
    
    Cas : file=178 (16:9), content=177 (16:9), screen=177 (16:9)
    - Barres encodées : file (178) > content (177) → encoded_zoom = 178/177 = 1.0056
    - Barres affichage : content (177) = screen (177) → pas de zoom affichage
    - Zoom total : encoded_zoom seulement = 1.0056
    """
    file_ratio = 178
    detected_ratio = 177
    
    # Calcul manuel
    encoded_zoom_manual = file_ratio / float(detected_ratio)  # 178 / 177
    # Pas de display_zoom car detected_ratio == 177 (16:9)
    expected_total_manual = encoded_zoom_manual
    
    # Calcul par le code
    zoom_value = zoom._calculate_zoom(detected_ratio, file_ratio=file_ratio)
    
    # Vérification
    assert abs(zoom_value - expected_total_manual) < 0.001, \
        f"Zoom encodé seul incorrect: attendu {expected_total_manual:.4f}, obtenu {zoom_value:.4f}"


def test_display_bars_only_no_encoded_bars(zoom):
    """
    Test : barres affichage uniquement, pas de barres encodées
    
    Cas : file=235 (2.35:1), content=235 (2.35:1), screen=177 (16:9)
    - Barres encodées : file == content → pas de barres encodées
    - Barres affichage : content (235) > screen (177) → display_zoom = 235/177 = 1.3277
    - Zoom total : display_zoom seulement = 1.3277
    """
    file_ratio = 235
    detected_ratio = 235
    
    # Calcul manuel
    # Pas d'encoded_zoom car file_ratio == detected_ratio
    display_zoom_manual = detected_ratio / 177.0  # 235 / 177
    expected_total_manual = display_zoom_manual
    
    # Calcul par le code
    zoom_value = zoom._calculate_zoom(detected_ratio, file_ratio=file_ratio)
    
    # Vérification
    assert abs(zoom_value - expected_total_manual) < 0.001, \
        f"Zoom affichage seul incorrect: attendu {expected_total_manual:.4f}, obtenu {zoom_value:.4f}"


def test_zoom_multiplication_property(zoom):
    """
    Test de propriété : vérifier que la multiplication des zooms est cohérente
    
    Propriété : Si on a deux transformations successives :
    - Transformation 1 : zoom de z1
    - Transformation 2 : zoom de z2
    - Transformation totale : z1 × z2
    
    Vérifie que cette propriété est respectée dans le calcul combiné.
    """
    # Cas avec barres encodées et affichage
    file_ratio = 240
    detected_ratio = 235
    
    # Zoom encodé seul
    encoded_zoom = file_ratio / float(detected_ratio)
    
    # Zoom affichage seul (si pas de barres encodées)
    display_zoom = detected_ratio / 177.0
    
    # Zoom combiné (avec barres encodées)
    combined_zoom = zoom._calculate_zoom(detected_ratio, file_ratio=file_ratio)
    
    # Vérification : combined_zoom devrait être proche de encoded_zoom × display_zoom
    expected_combined = encoded_zoom * display_zoom
    assert abs(combined_zoom - expected_combined) < 0.001, \
        f"Propriété de multiplication non respectée: {combined_zoom:.4f} != {expected_combined:.4f}"

