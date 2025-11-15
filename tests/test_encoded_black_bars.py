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
    
    ratio = service._detect_aspect_ratio()
    
    # Vérifier que le ratio IMDb est retourné
    assert ratio == 235
    
    # Vérifier qu'un log de détection a été créé
    import xbmc
    log_messages = [msg for msg, level in xbmc.logs if "Encoded black bars detected" in msg]
    assert len(log_messages) > 0, "Should log encoded black bars detection"


def test_no_encoded_black_bars_similar_ratios():
    """Test pas de barres encodées : ratios similaires (IMDb 235, fichier 237)"""
    # Mocker : IMDb ratio 235, File ratio 237 (différence < seuil)
    mock_getInfoLabel(237)
    mock_executeJSONRPC("tt1234567")
    
    service = Service()
    video_tag = MockVideoInfoTag(title="Test Movie", year=2020)
    
    service.cache._cache = {}
    service.cache.get = lambda *args, **kwargs: None
    service.imdb.get_aspect_ratio = lambda title, imdb_number=None: 235
    service.isPlayingVideo = lambda: True
    service.getVideoInfoTag = lambda: video_tag
    
    ratio = service._detect_aspect_ratio()
    
    # Vérifier que le ratio IMDb est retourné
    assert ratio == 235
    
    # Vérifier qu'aucun log de détection n'a été créé
    import xbmc
    log_messages = [msg for msg, level in xbmc.logs if "Encoded black bars detected" in msg]
    assert len(log_messages) == 0, "Should not log encoded black bars for similar ratios"


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
    
    ratio = service._detect_aspect_ratio()
    
    # Vérifier que le ratio IMDb est retourné
    assert ratio == 235
    
    # Vérifier qu'aucun log de détection n'a été créé
    import xbmc
    log_messages = [msg for msg, level in xbmc.logs if "Encoded black bars detected" in msg]
    assert len(log_messages) == 0, "Should not log encoded black bars for identical ratios"


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
    
    ratio = service._detect_aspect_ratio()
    
    # Vérifier que le ratio fichier est retourné
    assert ratio == 178
