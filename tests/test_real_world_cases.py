"""
Tests pour les cas réels du fichier CASES.jsonl.
"""
import sys
import os
import json
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
    zoom = ZoomApplier()
    # Mocker xbmcgui pour retourner window_id 12005 (fullscreen)
    import xbmcgui
    xbmcgui.getCurrentWindowId = lambda: 12005
    # Mocker xbmc.executeJSONRPC
    import xbmc
    xbmc.executeJSONRPC = lambda cmd: None
    return zoom


def load_test_cases():
    """Charge les cas de test depuis CASES.jsonl"""
    cases_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'CASES.jsonl')
    cases = []
    with open(cases_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    case = json.loads(line)
                    cases.append(case)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Erreur de parsing JSON dans CASES.jsonl: {e}")
    return cases


@pytest.mark.parametrize("case", load_test_cases())
def test_real_world_case(zoom, case):
    """Test chaque cas réel du fichier CASES.jsonl"""
    title = case.get('title', 'Unknown')
    imdb_ratio = case.get('imdb_ratio')
    file_ratio = case.get('file_ratio')
    ideal_zoom = case.get('ideal_zoom')
    
    # Déterminer si on doit zoomer les ratios étroits
    # Pour les ratios < 177, on active zoom_narrow_ratios
    zoom_narrow_ratios = imdb_ratio < 177 if imdb_ratio else False
    
    # Calculer le zoom avec la logique actuelle
    calculated_zoom = zoom._calculate_zoom(
        detected_ratio=imdb_ratio,
        zoom_narrow_ratios=zoom_narrow_ratios,
        file_ratio=file_ratio
    )
    
    # Appliquer l'offset par défaut de 0.01 (comme dans les settings)
    zoom_offset = 0.01
    calculated_zoom_with_offset = calculated_zoom + zoom_offset
    
    # Comparer avec le zoom idéal (tolérance de 0.05 pour les variations acceptables)
    difference = abs(calculated_zoom_with_offset - ideal_zoom)
    tolerance = 0.05
    
    assert difference < tolerance, (
        f"Cas '{title}' (IMDb={imdb_ratio}, file={file_ratio}): "
        f"zoom calculé={calculated_zoom:.4f}, zoom avec offset={calculated_zoom_with_offset:.4f}, zoom idéal={ideal_zoom:.4f}, "
        f"différence={difference:.4f} (tolérance={tolerance}). "
        f"Ce cas nécessite peut-être une amélioration de la logique."
    )

