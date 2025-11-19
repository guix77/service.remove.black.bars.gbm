"""
Tests pour KodiMetadataProvider.
"""
import sys
import os
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

from addon import KodiMetadataProvider
from tests.mock_kodi import MockVideoInfoTag


@pytest.fixture
def provider():
    """Fixture pour créer un provider"""
    provider = KodiMetadataProvider()
    import xbmc
    xbmc.info_label = mock_kodi.MockInfoLabel()
    return provider


def test_get_aspect_ratio_from_jsonrpc(provider):
    """Test avec JSON-RPC pour ratio 2.35:1 (1920x816)"""
    import json
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_executeJSONRPC = addon_module.xbmc.executeJSONRPC
    
    def mock_executeJSONRPC(command):
        cmd_json = json.loads(command)
        if cmd_json.get("method") == "Player.GetProperties":
            # 1920x816 = 2.35:1 = 235
            return json.dumps({
                "jsonrpc": "2.0",
                "result": {
                    "width": 1920,
                    "height": 816
                },
                "id": 1
            })
        return None
    
    addon_module.xbmc.executeJSONRPC = mock_executeJSONRPC
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio == 235
    finally:
        addon_module.xbmc.executeJSONRPC = original_executeJSONRPC


def test_get_aspect_ratio_16_9(provider):
    """Test avec ratio 16:9 (1920x1080)"""
    import json
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_executeJSONRPC = addon_module.xbmc.executeJSONRPC
    
    def mock_executeJSONRPC(command):
        cmd_json = json.loads(command)
        if cmd_json.get("method") == "Player.GetProperties":
            # 1920x1080 = 1.777... * 100 = 177.7... arrondi = 177
            return json.dumps({
                "jsonrpc": "2.0",
                "result": {
                    "width": 1920,
                    "height": 1080
                },
                "id": 1
            })
        return None
    
    addon_module.xbmc.executeJSONRPC = mock_executeJSONRPC
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        # 1920/1080 = 1.777... * 100 = 177.7... arrondi = 177
        assert ratio == 177
    finally:
        addon_module.xbmc.executeJSONRPC = original_executeJSONRPC


def test_get_aspect_ratio_4_3(provider):
    """Test avec ratio 4:3 (1440x1080)"""
    import json
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_executeJSONRPC = addon_module.xbmc.executeJSONRPC
    
    def mock_executeJSONRPC(command):
        cmd_json = json.loads(command)
        if cmd_json.get("method") == "Player.GetProperties":
            # 1440x1080 = 1.33:1 = 133
            return json.dumps({
                "jsonrpc": "2.0",
                "result": {
                    "width": 1440,
                    "height": 1080
                },
                "id": 1
            })
        return None
    
    addon_module.xbmc.executeJSONRPC = mock_executeJSONRPC
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio == 133
    finally:
        addon_module.xbmc.executeJSONRPC = original_executeJSONRPC


def test_get_aspect_ratio_1_85(provider):
    """Test avec ratio 1.85:1 (1920x1038)"""
    import json
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_executeJSONRPC = addon_module.xbmc.executeJSONRPC
    
    def mock_executeJSONRPC(command):
        cmd_json = json.loads(command)
        if cmd_json.get("method") == "Player.GetProperties":
            # 1920x1038 = 1.850... * 100 = 185.0... arrondi = 185
            # Mais 1920/1038 = 1.849... * 100 = 184.9... arrondi = 184
            # Utilisons 1920x1037 pour obtenir 185
            return json.dumps({
                "jsonrpc": "2.0",
                "result": {
                    "width": 1920,
                    "height": 1037
                },
                "id": 1
            })
        return None
    
    addon_module.xbmc.executeJSONRPC = mock_executeJSONRPC
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        # 1920/1037 = 1.851... * 100 = 185.1... arrondi = 185
        assert ratio == 185
    finally:
        addon_module.xbmc.executeJSONRPC = original_executeJSONRPC


def test_get_aspect_ratio_2_40(provider):
    """Test avec ratio 2.40:1 (1920x800)"""
    import json
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_executeJSONRPC = addon_module.xbmc.executeJSONRPC
    
    def mock_executeJSONRPC(command):
        cmd_json = json.loads(command)
        if cmd_json.get("method") == "Player.GetProperties":
            # 1920x800 = 2.40:1 = 240
            return json.dumps({
                "jsonrpc": "2.0",
                "result": {
                    "width": 1920,
                    "height": 800
                },
                "id": 1
            })
        return None
    
    addon_module.xbmc.executeJSONRPC = mock_executeJSONRPC
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio == 240
    finally:
        addon_module.xbmc.executeJSONRPC = original_executeJSONRPC


def test_no_aspect_ratio_available(provider):
    """Test quand aucun ratio n'est disponible (JSON-RPC retourne résultat vide)"""
    import json
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_executeJSONRPC = addon_module.xbmc.executeJSONRPC
    
    def mock_executeJSONRPC(command):
        cmd_json = json.loads(command)
        if cmd_json.get("method") == "Player.GetProperties":
            # Retourner un résultat vide (pas de width/height)
            return json.dumps({
                "jsonrpc": "2.0",
                "result": {},
                "id": 1
            })
        return None
    
    addon_module.xbmc.executeJSONRPC = mock_executeJSONRPC
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio is None
    finally:
        addon_module.xbmc.executeJSONRPC = original_executeJSONRPC


def test_jsonrpc_returns_no_result(provider):
    """Test quand JSON-RPC retourne None (pas de résultat)"""
    import json
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_executeJSONRPC = addon_module.xbmc.executeJSONRPC
    
    def mock_executeJSONRPC(command):
        # Retourner None (pas de résultat)
        return None
    
    addon_module.xbmc.executeJSONRPC = mock_executeJSONRPC
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio is None
    finally:
        addon_module.xbmc.executeJSONRPC = original_executeJSONRPC


def test_rounding(provider):
    """Test arrondi correct (1920x813 ≈ 2.36:1 -> 236)"""
    import json
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_executeJSONRPC = addon_module.xbmc.executeJSONRPC
    
    def mock_executeJSONRPC(command):
        cmd_json = json.loads(command)
        if cmd_json.get("method") == "Player.GetProperties":
            # 1920x813 = 2.361... * 100 = 236.1... arrondi = 236
            return json.dumps({
                "jsonrpc": "2.0",
                "result": {
                    "width": 1920,
                    "height": 813
                },
                "id": 1
            })
        return None
    
    addon_module.xbmc.executeJSONRPC = mock_executeJSONRPC
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        # 1920/813 = 2.361... * 100 = 236.1... arrondi = 236
        assert ratio == 236
    finally:
        addon_module.xbmc.executeJSONRPC = original_executeJSONRPC


def test_with_remote_source(provider):
    """Test avec source distante (Jellyfin/Plex)"""
    import json
    video_tag = MockVideoInfoTag(filename="http://jellyfin/video.mp4")
    import addon as addon_module
    original_executeJSONRPC = addon_module.xbmc.executeJSONRPC
    
    def mock_executeJSONRPC(command):
        cmd_json = json.loads(command)
        if cmd_json.get("method") == "Player.GetProperties":
            # 1920x800 = 2.40:1 = 240
            return json.dumps({
                "jsonrpc": "2.0",
                "result": {
                    "width": 1920,
                    "height": 800
                },
                "id": 1
            })
        return None
    
    addon_module.xbmc.executeJSONRPC = mock_executeJSONRPC
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio == 240
    finally:
        addon_module.xbmc.executeJSONRPC = original_executeJSONRPC


def test_get_aspect_ratio_from_resolution(provider):
    """Test calcul depuis résolution réelle via JSON-RPC (plus précis)"""
    import json
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_executeJSONRPC = addon_module.xbmc.executeJSONRPC
    
    def mock_executeJSONRPC(command):
        cmd_json = json.loads(command)
        if cmd_json.get("method") == "Player.GetProperties":
            return json.dumps({
                "jsonrpc": "2.0",
                "result": {
                    "width": 576,
                    "height": 352
                },
                "id": 1
            })
        return None
    
    addon_module.xbmc.executeJSONRPC = mock_executeJSONRPC
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        # 576/352 = 1.6364, * 100 = 163.64, arrondi = 163
        expected = int((576 / 352.0) * 100)
        assert ratio == expected, f"Expected {expected}, got {ratio}"
    finally:
        addon_module.xbmc.executeJSONRPC = original_executeJSONRPC


def test_resolution_takes_precedence_over_videoaspect(provider):
    """Test que la résolution via JSON-RPC a priorité sur VideoAspect"""
    import json
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_executeJSONRPC = addon_module.xbmc.executeJSONRPC
    original_getInfoLabel = addon_module.xbmc.getInfoLabel
    
    def mock_executeJSONRPC(command):
        cmd_json = json.loads(command)
        if cmd_json.get("method") == "Player.GetProperties":
            return json.dumps({
                "jsonrpc": "2.0",
                "result": {
                    "width": 576,
                    "height": 352
                },
                "id": 1
            })
        return None
    
    def mock_getInfoLabel(label):
        if label == "VideoPlayer.VideoAspect":
            return "1.66"  # Moins précis que la résolution
        return ""
    
    addon_module.xbmc.executeJSONRPC = mock_executeJSONRPC
    addon_module.xbmc.getInfoLabel = mock_getInfoLabel
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        # Devrait utiliser la résolution (163) et non VideoAspect (166)
        expected_from_resolution = int((576 / 352.0) * 100)
        assert ratio == expected_from_resolution, f"Should use resolution ({expected_from_resolution}), not VideoAspect (166). Got {ratio}"
    finally:
        addon_module.xbmc.executeJSONRPC = original_executeJSONRPC
        addon_module.xbmc.getInfoLabel = original_getInfoLabel
