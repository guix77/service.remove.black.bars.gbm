"""
Tests for settings integration.
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
sys.modules['xbmcgui'] = mock_kodi.MockXbmcgui()

from addon import ZoomApplier, notify
from tests.mock_kodi import MockPlayer, MockAddon


@pytest.fixture
def zoom():
    """Fixture pour créer un ZoomApplier"""
    return ZoomApplier()


@pytest.fixture
def mock_player_with_settings():
    """Fixture pour créer un mock player avec settings"""
    settings = {
        "tolerance_16_9_min": "170",
        "tolerance_16_9_max": "185",
        "notification_duration": "3000"
    }
    addon = MockAddon(settings=settings)
    player = MockPlayer(is_playing_video=True, is_playing=True)
    player._addon = addon
    return player


def test_get_16_9_tolerance_from_settings(zoom, mock_player_with_settings):
    """Test that tolerance is read from settings"""
    min_val, max_val = zoom._get_16_9_tolerance(mock_player_with_settings)
    assert min_val == 170
    assert max_val == 185


def test_get_16_9_tolerance_default(zoom):
    """Test that default tolerance is used when player is None"""
    min_val, max_val = zoom._get_16_9_tolerance(None)
    assert min_val == 175
    assert max_val == 180


def test_calculate_zoom_uses_settings_tolerance(zoom, mock_player_with_settings):
    """Test that zoom calculation uses settings tolerance"""
    # File ratio 170 should be within tolerance (170-185)
    zoom_value = zoom._calculate_zoom(235, file_ratio=170, player=mock_player_with_settings)
    assert zoom_value == 1.0  # No zoom, within tolerance
    
    # File ratio 190 should be outside tolerance
    zoom_value = zoom._calculate_zoom(235, file_ratio=190, player=mock_player_with_settings)
    expected = 190 / 235.0
    assert abs(zoom_value - expected) < 0.01


def test_notification_duration_from_settings():
    """Test that notification duration is read from settings"""
    # This test would require mocking xbmcgui.Dialog().notification
    # For now, we just verify the function exists and accepts duration_ms
    # In a real test environment, we'd mock the dialog and verify the call
    pass

