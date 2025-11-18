"""
Tests pour la détection des barres noires encodées.
"""
import sys
import os
import json
import pytest

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mocker les modules Kodi avant d'importer addon
import tests.mock_kodi as mock_kodi
mock_xbmc = mock_kodi.MockXbmc()
sys.modules['xbmc'] = mock_xbmc
sys.modules['xbmcaddon'] = type(sys)('xbmcaddon')
sys.modules['xbmcaddon'].Addon = lambda: mock_kodi.MockAddon()
sys.modules['xbmcgui'] = mock_kodi.MockXbmcgui()

from addon import Service
from tests.mock_kodi import MockVideoInfoTag
import addon as addon_module


@pytest.fixture(autouse=True)
def setup_test():
    """Fixture automatique pour chaque test - réinitialise les mocks globaux"""
    # S'assurer que addon_module.xbmc pointe vers le mock_xbmc actuel
    sys.modules['xbmc'] = mock_xbmc
    addon_module.xbmc = mock_xbmc
    
    # Sauvegarder les fonctions originales depuis mock_xbmc (toujours les vraies originales)
    original_getInfoLabel = mock_xbmc.getInfoLabel
    original_executeJSONRPC = mock_xbmc.executeJSONRPC
    original_getOriginalAspectRatio = addon_module.getOriginalAspectRatio
    
    # Mocker le addon pour chaque test
    mock_addon = mock_kodi.MockAddon(settings={
        "enable_imdb": "true",
        "enable_cache": "false",
        "zoom_narrow_ratios": "false"
    })
    sys.modules['xbmcaddon'].Addon = lambda: mock_addon
    # S'assurer que addon_module utilise aussi le mock
    if hasattr(addon_module, 'xbmcaddon'):
        addon_module.xbmcaddon.Addon = lambda: mock_addon
    
    # Réinitialiser les logs
    import xbmc
    xbmc.logs = []
    
    # Restaurer les mocks globaux aux fonctions originales de mock_xbmc
    addon_module.xbmc.getInfoLabel = original_getInfoLabel
    addon_module.xbmc.executeJSONRPC = original_executeJSONRPC
    addon_module.getOriginalAspectRatio = original_getOriginalAspectRatio
    
    yield
    
    # Nettoyer après le test - restaurer aux fonctions originales de mock_xbmc
    addon_module.xbmc.getInfoLabel = mock_xbmc.getInfoLabel
    addon_module.xbmc.executeJSONRPC = mock_xbmc.executeJSONRPC
    addon_module.getOriginalAspectRatio = original_getOriginalAspectRatio


def mock_getInfoLabel(file_ratio):
    """Helper pour mocker getInfoLabel avec un ratio de fichier"""
    def mock_func(label):
        if label == "VideoPlayer.VideoAspect":
            return str(file_ratio / 100.0) if file_ratio else ""
        return ""
    addon_module.xbmc.getInfoLabel = mock_func


def mock_executeJSONRPC(imdb_number=None):
    """Helper pour mocker executeJSONRPC"""
    def mock_func(command):
        cmd = json.loads(command)
        if cmd.get("method") == "Player.GetItem":
            if "uniqueid" in cmd.get("params", {}).get("properties", []):
                result = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "item": {
                            "type": "movie",
                            "uniqueid": {}
                        }
                    }
                }
                if imdb_number:
                    result["result"]["item"]["uniqueid"]["imdb"] = imdb_number
                return json.dumps(result)
        return json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}})
    addon_module.xbmc.executeJSONRPC = mock_func


def test_detect_encoded_black_bars():
    """Test détection de barres encodées : IMDb 235, fichier 178"""
    # Mocker : IMDb ratio 235 (2.35:1), File ratio 178 (16:9)
    mock_getInfoLabel(178)
    mock_executeJSONRPC("tt1234567")
    
    service = Service()
    video_tag = MockVideoInfoTag(title="Test Movie", year=2020)
    
    # Désactiver le cache
    service.cache._cache = {}
    service.cache.get = lambda *args, **kwargs: None
    
    # Mocker IMDb
    service.imdb.get_aspect_ratio = lambda title, imdb_number=None: 235
    
    # Mocker isPlayingVideo
    service.isPlayingVideo = lambda: True
    service.getVideoInfoTag = lambda: video_tag
    
    result = service._detect_aspect_ratio()
    
    # Vérifier que le ratio IMDb est retourné (premier élément du tuple)
    assert result is not None
    detected_ratio, file_ratio, title_display = result
    assert detected_ratio == 235
    assert file_ratio == 178
    
    # Vérifier qu'un log indiquant la différence ou les barres encodées a été créé
    import xbmc
    log_messages = [msg for msg, level in xbmc.logs if "Encoded black bars detected" in msg or "File ratio differs from IMDb" in msg]
    assert len(log_messages) > 0, "Should log file ratio difference or encoded bars detection"


def test_no_encoded_black_bars_similar_ratios():
    """Test pas de barres encodées : ratios similaires (IMDb 235, fichier 237)
    - Différence: 2 < threshold (11) MAIS ni file ni content proches de 16:9
    - Avec la nouvelle logique : file_ratio EST utilisé (différence > 0 ET ni file ni content proches 16:9)
    """
    # Mocker : IMDb ratio 235, File ratio 237 (différence < seuil mais ni proche 16:9)
    mock_getInfoLabel(237)
    mock_executeJSONRPC("tt1234567")
    
    service = Service()
    video_tag = MockVideoInfoTag(title="Test Movie", year=2020)
    
    service.cache._cache = {}
    service.cache.get = lambda *args, **kwargs: None
    service.imdb.get_aspect_ratio = lambda title, imdb_number=None: 235
    service.isPlayingVideo = lambda: True
    service.getVideoInfoTag = lambda: video_tag
    
    result = service._detect_aspect_ratio()
    
    # Vérifier que le ratio IMDb est retourné (premier élément du tuple)
    assert result is not None
    detected_ratio, file_ratio, title_display = result
    assert detected_ratio == 235
    # file_ratio EST utilisé car différence > 0 ET ni file ni content proches de 16:9
    assert file_ratio == 237, "file_ratio should be used when difference > 0 and neither close to 16:9"


def test_no_encoded_black_bars_identical_ratios():
    """Test pas de barres encodées : ratios identiques"""
    # Mocker : IMDb ratio 235, File ratio 235 (identique)
    mock_getInfoLabel(235)
    mock_executeJSONRPC("tt1234567")
    
    service = Service()
    video_tag = MockVideoInfoTag(title="Test Movie", year=2020)
    
    service.cache._cache = {}
    service.cache.get = lambda *args, **kwargs: None
    # Mocker service.imdb directement
    service.imdb.get_aspect_ratio = lambda title, imdb_number=None: 235
    service.isPlayingVideo = lambda: True
    service.getVideoInfoTag = lambda: video_tag
    
    result = service._detect_aspect_ratio()
    
    # Vérifier que le ratio IMDb est retourné (premier élément du tuple)
    assert result is not None
    detected_ratio, file_ratio, title_display = result
    assert detected_ratio == 235
    # file_ratio is NOT returned if identical to detected_ratio (no encoded bars)
    assert file_ratio is None
    
    # Vérifier que file_ratio n'est pas utilisé (ratios identiques)


def test_fallback_to_file_ratio_when_no_imdb():
    """Test fallback vers ratio fichier quand IMDb n'est pas disponible"""
    # Mocker : Pas de ratio IMDb, File ratio 178
    mock_getInfoLabel(178)
    mock_executeJSONRPC(None)
    
    service = Service()
    video_tag = MockVideoInfoTag(title="Test Movie", year=2020)
    
    service.cache._cache = {}
    service.cache.get = lambda *args, **kwargs: None
    service.isPlayingVideo = lambda: True
    service.getVideoInfoTag = lambda: video_tag
    
    # Mocker IMDbProvider pour retourner None
    service.imdb.get_aspect_ratio = lambda title, imdb_number=None: None
    
    # Désactiver IMDb pour forcer le fallback
    mock_addon = mock_kodi.MockAddon(settings={
        "enable_imdb": "false",
        "enable_cache": "false",
        "zoom_narrow_ratios": "false"
    })
    sys.modules['xbmcaddon'].Addon = lambda: mock_addon
    if hasattr(addon_module, 'xbmcaddon'):
        addon_module.xbmcaddon.Addon = lambda: mock_addon
    service._addon = mock_addon
    
    result = service._detect_aspect_ratio()
    
    # Vérifier que le ratio fichier est retourné (premier élément du tuple)
    assert result is not None
    detected_ratio, file_ratio, title_display = result
    assert detected_ratio == 178
    # When IMDb is disabled, file_ratio is used as detected_ratio
    assert file_ratio == 178


def test_vertical_encoded_bars_narrower_file():
    """Test barres encodées verticales : file_ratio < detected_ratio ET file_ratio proche de 16:9
    - File ratio: 175 (16:9 avec barres encodées verticales)
    - IMDb ratio: 185 (1.85:1 contenu réel)
    - Différence: 10 > threshold (9) ✓
    - Zoom attendu: (185/175) * (185/177) pour enlever barres encodées + affichage
    """
    from addon import ZoomApplier
    
    # Mocker : IMDb ratio 185, File ratio 175 (proche de 16:9, diff=10 > threshold=9)
    mock_getInfoLabel(175)
    mock_executeJSONRPC("tt1234567")
    
    service = Service()
    video_tag = MockVideoInfoTag(title="Test Movie", year=2020)
    
    # Désactiver le cache
    service.cache._cache = {}
    service.cache.get = lambda *args, **kwargs: None
    
    # Mocker IMDb
    service.imdb.get_aspect_ratio = lambda title, imdb_number=None: 185
    
    # Mocker isPlayingVideo
    service.isPlayingVideo = lambda: True
    service.getVideoInfoTag = lambda: video_tag
    
    # Détecter le ratio
    result = service._detect_aspect_ratio()
    
    # Vérifier la détection
    assert result is not None
    detected_ratio, file_ratio, title_display = result
    assert detected_ratio == 185, "Should detect IMDb ratio 185"
    assert file_ratio == 175, "Should detect file ratio 175 (close to 16:9)"
    
    # Vérifier qu'un log indiquant la différence ou les barres encodées a été créé
    import xbmc
    log_messages = [msg for msg, level in xbmc.logs if "Encoded black bars detected" in msg or "File ratio differs from IMDb" in msg]
    assert len(log_messages) > 0, "Should log file ratio difference or encoded bars detection"
    
    # Vérifier le calcul du zoom
    zoom = ZoomApplier()
    zoom_value = zoom._calculate_zoom(detected_ratio, file_ratio=file_ratio)
    # Combined zoom: encoded (185/175) * display (185/177)
    encoded_zoom = 185 / 175.0
    display_zoom = 185 / 177.0
    expected = encoded_zoom * display_zoom
    assert abs(zoom_value - expected) < 0.01, f"Zoom should be {expected:.3f}, got {zoom_value:.3f}"
    assert zoom_value > 1.0, "Zoom should be greater than 1.0 to remove vertical encoded bars"


def test_no_encoded_bars_if_file_not_16_9():
    """Test que file_ratio EST utilisé directement si ni file ni content ne sont proches de 16:9
    - File ratio: 166 (1.66:1, pas proche de 16:9)
    - IMDb ratio: 185 (1.85:1, pas proche de 16:9)
    - Différence: 19 > threshold (9) ET ni file ni content proche de 16:9
    - file_ratio EST utilisé directement (cas Basil/Le Baron Rouge)
    """
    # Mocker : IMDb ratio 185, File ratio 166 (ni l'un ni l'autre proche de 16:9)
    mock_getInfoLabel(166)
    mock_executeJSONRPC("tt1234567")
    
    service = Service()
    video_tag = MockVideoInfoTag(title="Test Movie", year=2020)
    
    # Désactiver le cache
    service.cache._cache = {}
    service.cache.get = lambda *args, **kwargs: None
    
    # Mocker IMDb
    service.imdb.get_aspect_ratio = lambda title, imdb_number=None: 185
    
    # Mocker isPlayingVideo
    service.isPlayingVideo = lambda: True
    service.getVideoInfoTag = lambda: video_tag
    
    # Détecter le ratio
    result = service._detect_aspect_ratio()
    
    # Vérifier la détection
    assert result is not None
    detected_ratio, file_ratio, title_display = result
    assert detected_ratio == 185, "Should detect IMDb ratio 185"
    # file_ratio EST utilisé car ni file ni content proche de 16:9 (nouvelle logique)
    assert file_ratio == 166, "Should use file_ratio (neither close to 16:9, use file_ratio directly)"
    
    # Vérifier le calcul du zoom (avec file_ratio, zoom direct file_ratio -> 16:9)
    from addon import ZoomApplier
    zoom = ZoomApplier()
    zoom_value = zoom._calculate_zoom(detected_ratio, file_ratio=file_ratio)
    # file_ratio (166) < 177: direct_zoom = 177 / 166 = 1.066
    expected = 177.0 / 166
    assert abs(zoom_value - expected) < 0.01, f"Zoom should be {expected:.3f}, got {zoom_value:.3f}"
