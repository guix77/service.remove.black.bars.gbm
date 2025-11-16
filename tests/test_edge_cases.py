"""
Tests for edge cases.
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

from addon import ZoomApplier, JsonCacheProvider
from tests.mock_kodi import MockPlayer


@pytest.fixture
def zoom():
    """Fixture pour créer un ZoomApplier"""
    return ZoomApplier()


@pytest.fixture
def mock_player():
    """Fixture pour créer un mock player"""
    return MockPlayer(is_playing_video=True, is_playing=True)


def test_calculate_zoom_file_ratio_exactly_16_9(zoom):
    """Test zoom when file ratio is exactly 16:9 (177)"""
    zoom_value = zoom._calculate_zoom(235, file_ratio=177)
    assert zoom_value == 1.0  # No zoom needed


def test_calculate_zoom_file_ratio_at_tolerance_boundary(zoom):
    """Test zoom at tolerance boundaries"""
    # At min boundary (175)
    zoom_value = zoom._calculate_zoom(235, file_ratio=175)
    assert zoom_value == 1.0
    
    # At max boundary (180)
    zoom_value = zoom._calculate_zoom(235, file_ratio=180)
    assert zoom_value == 1.0
    
    # Just below min (174)
    zoom_value = zoom._calculate_zoom(235, file_ratio=174)
    expected = 174 / 235.0
    assert abs(zoom_value - expected) < 0.01
    
    # Just above max (181)
    zoom_value = zoom._calculate_zoom(235, file_ratio=181)
    expected = 181 / 235.0
    assert abs(zoom_value - expected) < 0.01


def test_calculate_zoom_identical_ratios(zoom):
    """Test zoom when detected and file ratios are identical"""
    zoom_value = zoom._calculate_zoom(235, file_ratio=235)
    expected = 235 / 177.0
    assert abs(zoom_value - expected) < 0.01


def test_calculate_zoom_file_ratio_wider_than_detected(zoom):
    """Test zoom when file ratio is wider than detected (unusual case)"""
    # This shouldn't happen in practice, but test the logic
    zoom_value = zoom._calculate_zoom(235, file_ratio=240)
    expected = 240 / 235.0
    assert abs(zoom_value - expected) < 0.01


def test_cache_store_invalid_ratio():
    """Test that invalid ratios are not stored in cache"""
    cache = JsonCacheProvider(enabled=False)
    cache._cache = {}
    
    # Try to store invalid ratios
    cache.store("Movie", 2020, 99)  # Too low
    cache.store("Movie2", 2020, 501)  # Too high
    cache.store("Movie3", 2020, None)  # None
    
    # Cache should be empty
    assert len(cache._cache) == 0


def test_cache_get_invalid_cached_ratio():
    """Test that invalid cached ratios are not returned"""
    cache = JsonCacheProvider(enabled=False)
    cache._cache = {}
    
    # Manually add invalid ratio to cache
    cache._cache["test movie (2020)"] = 99  # Invalid
    
    # Get should return None (but doesn't remove invalid entries automatically)
    result = cache.get("test movie", 2020)
    assert result is None

