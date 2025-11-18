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
    """Test zoom when file ratio is exactly 16:9 (177) and same as detected_ratio"""
    # If file_ratio == detected_ratio and both are 16:9, no zoom needed
    zoom_value = zoom._calculate_zoom(177, file_ratio=177)
    assert zoom_value == 1.0  # No zoom needed
    
    # If file_ratio is 16:9 but detected_ratio is different, calculate encoded bars zoom
    zoom_value = zoom._calculate_zoom(235, file_ratio=177)
    # This shouldn't happen in practice (file_ratio only passed if encoded bars detected)
    # But if it does, we calculate zoom for encoded bars
    encoded_zoom = 235 / 177.0
    display_zoom = 235 / 177.0
    expected = encoded_zoom * display_zoom
    assert abs(zoom_value - expected) < 0.01


def test_calculate_zoom_file_ratio_at_tolerance_boundary(zoom):
    """Test zoom at tolerance boundaries"""
    # At min boundary (175) - if same as detected_ratio, no zoom
    zoom_value = zoom._calculate_zoom(175, file_ratio=175)
    assert zoom_value == 1.0
    
    # At max boundary (180) - if same as detected_ratio, no zoom
    zoom_value = zoom._calculate_zoom(180, file_ratio=180)
    assert zoom_value == 1.0
    
    # At min boundary (175) but different from detected_ratio - calculate encoded bars zoom
    zoom_value = zoom._calculate_zoom(235, file_ratio=175)
    encoded_zoom = 235 / 175.0
    display_zoom = 235 / 177.0
    expected = encoded_zoom * display_zoom
    assert abs(zoom_value - expected) < 0.01
    
    # At max boundary (180) but different from detected_ratio - calculate encoded bars zoom
    zoom_value = zoom._calculate_zoom(235, file_ratio=180)
    encoded_zoom = 235 / 180.0
    display_zoom = 235 / 177.0
    expected = encoded_zoom * display_zoom
    assert abs(zoom_value - expected) < 0.01
    
    # Just below min (174) - neither close to 16:9, use file_ratio directly
    zoom_value = zoom._calculate_zoom(235, file_ratio=174)
    # file_ratio (174) < 177: direct_zoom = 177 / 174
    expected = 177.0 / 174
    assert abs(zoom_value - expected) < 0.01
    
    # Just above max (181) - neither close to 16:9, use file_ratio directly
    zoom_value = zoom._calculate_zoom(235, file_ratio=181)
    # file_ratio (181) > 177: direct_zoom = 181 / 177
    expected = 181.0 / 177.0
    assert abs(zoom_value - expected) < 0.01


def test_calculate_zoom_identical_ratios(zoom):
    """Test zoom when detected and file ratios are identical
    - If within 16:9 tolerance: no zoom (no bars at all)
    - If outside 16:9 tolerance: zoom for display bars only (no encoded bars, but display bars exist)
    """
    # Identical ratios within 16:9 tolerance → no zoom
    zoom_value = zoom._calculate_zoom(177, file_ratio=177)
    assert zoom_value == 1.0, "Identical ratios within 16:9 tolerance should return 1.0"
    
    # Identical ratios outside 16:9 tolerance → zoom for display bars
    zoom_value = zoom._calculate_zoom(235, file_ratio=235)
    expected = 235 / 177.0
    assert abs(zoom_value - expected) < 0.01, f"Identical ratios outside 16:9 tolerance should zoom for display bars: expected {expected:.3f}, got {zoom_value:.3f}"


def test_calculate_zoom_file_ratio_wider_than_detected(zoom):
    """Test zoom when file ratio is wider than detected (horizontal encoded bars)
    
    Example: file=240, content=235
    - Encoded zoom: 240/235 = 1.021 (to remove horizontal encoded bars)
    - Display zoom: 235/177 = 1.328 (to remove display bars)
    - Total zoom: 1.021 * 1.328 = 1.356
    """
    zoom_value = zoom._calculate_zoom(235, file_ratio=240)
    encoded_zoom = 240 / 235.0
    display_zoom = 235 / 177.0
    expected = encoded_zoom * display_zoom  # Combined zoom
    assert abs(zoom_value - expected) < 0.01
    assert zoom_value > 1.0, "Zoom should be > 1.0 to remove bars"


def test_calculate_zoom_file_ratio_narrower_than_detected(zoom):
    """Test zoom when file ratio is narrower than detected (vertical encoded bars)
    
    Example: file=166, content=185
    - Neither file (166) nor content (185) close to 16:9
    - Use file_ratio directly: 177 / 166 = 1.066 (to adapt file to 16:9)
    """
    zoom_value = zoom._calculate_zoom(185, file_ratio=166)
    # file_ratio (166) < 177: direct_zoom = 177 / 166
    expected = 177.0 / 166
    assert abs(zoom_value - expected) < 0.01
    assert zoom_value > 1.0, "Zoom should be greater than 1.0 to remove vertical encoded bars"


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

