"""
Tests pour ZoomApplier.
"""
import sys
import os
import time
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
from tests.mock_kodi import MockPlayer


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


@pytest.fixture
def mock_player():
    """Fixture pour créer un mock player"""
    return MockPlayer(is_playing_video=True, is_playing=True)


def test_calculate_zoom_ratio_235(zoom):
    """Test calcul zoom pour ratio 235 (2.35:1)"""
    zoom_value = zoom._calculate_zoom(235)
    expected = 235 / 177.0
    assert abs(zoom_value - expected) < 0.01


def test_calculate_zoom_ratio_200(zoom):
    """Test calcul zoom pour ratio 200 (2.00:1)"""
    zoom_value = zoom._calculate_zoom(200)
    expected = 200 / 177.0
    assert abs(zoom_value - expected) < 0.01


def test_calculate_zoom_ratio_185(zoom):
    """Test calcul zoom pour ratio 185 (1.85:1)"""
    zoom_value = zoom._calculate_zoom(185)
    expected = 185 / 177.0
    assert abs(zoom_value - expected) < 0.01


def test_calculate_zoom_ratio_177(zoom):
    """Test calcul zoom pour ratio 177 (16:9) - pas de zoom"""
    zoom_value = zoom._calculate_zoom(177)
    assert zoom_value == 1.0


def test_calculate_zoom_ratio_133(zoom):
    """Test calcul zoom pour ratio 133 (4:3) - pas de zoom"""
    zoom_value = zoom._calculate_zoom(133)
    assert zoom_value == 1.0


def test_calculate_zoom_ratio_240(zoom):
    """Test calcul zoom pour ratio 240 (2.40:1)"""
    zoom_value = zoom._calculate_zoom(240)
    expected = 240 / 177.0
    assert abs(zoom_value - expected) < 0.01


def test_no_zoom_if_ratio_less_than_177(zoom):
    """Test qu'il n'y a pas de zoom si ratio <= 177"""
    for ratio in [133, 177]:
        zoom_value = zoom._calculate_zoom(ratio)
        assert zoom_value == 1.0


def test_rate_limiting(zoom, mock_player):
    """Test rate limiting (500ms)"""
    # Premier zoom devrait fonctionner
    result1 = zoom.apply_zoom(235, mock_player)
    assert result1 is True
    
    # Deuxième zoom immédiatement après devrait être bloqué
    result2 = zoom.apply_zoom(240, mock_player)
    assert result2 is False
    
    # Attendre plus de 500ms
    time.sleep(0.6)
    result3 = zoom.apply_zoom(240, mock_player)
    assert result3 is True


def test_no_zoom_if_not_playing_video(zoom):
    """Test qu'il n'y a pas de zoom si vidéo ne joue pas"""
    not_playing_player = MockPlayer(is_playing_video=False, is_playing=False)
    result = zoom.apply_zoom(235, not_playing_player)
    assert result is False


def test_no_zoom_if_not_fullscreen(zoom, mock_player):
    """Test qu'il n'y a pas de zoom si pas en fullscreen"""
    import addon as addon_module
    # Créer un nouveau zoom pour éviter les effets de rate limiting
    new_zoom = ZoomApplier()
    # Sauvegarder la fonction originale
    original_getCurrentWindowId = addon_module.xbmcgui.getCurrentWindowId
    # Mocker getCurrentWindowId pour retourner window_id non-fullscreen
    addon_module.xbmcgui.getCurrentWindowId = lambda: 10000  # Home window, pas fullscreen
    try:
        result = new_zoom.apply_zoom(235, mock_player)
        assert result is False, "Zoom ne devrait pas être appliqué si pas en fullscreen"
    finally:
        # Restaurer
        addon_module.xbmcgui.getCurrentWindowId = original_getCurrentWindowId


def test_no_zoom_if_paused(zoom):
    """Test qu'il n'y a pas de zoom si vidéo en pause"""
    paused_player = MockPlayer(is_playing_video=True, is_playing=False)
    result = zoom.apply_zoom(235, paused_player)
    assert result is False
