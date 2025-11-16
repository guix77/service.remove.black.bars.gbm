"""
Tests for ratio validation.
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

from addon import ZoomApplier, MIN_VALID_RATIO, MAX_VALID_RATIO
from tests.mock_kodi import MockPlayer


@pytest.fixture
def zoom():
    """Fixture pour créer un ZoomApplier"""
    return ZoomApplier()


def test_validate_ratio_valid(zoom):
    """Test validation of valid ratios"""
    assert zoom._validate_ratio(100, "test") is True
    assert zoom._validate_ratio(177, "test") is True
    assert zoom._validate_ratio(235, "test") is True
    assert zoom._validate_ratio(500, "test") is True


def test_validate_ratio_invalid_too_low(zoom):
    """Test validation rejects ratios that are too low"""
    assert zoom._validate_ratio(99, "test") is False
    assert zoom._validate_ratio(50, "test") is False
    assert zoom._validate_ratio(0, "test") is False
    assert zoom._validate_ratio(-100, "test") is False


def test_validate_ratio_invalid_too_high(zoom):
    """Test validation rejects ratios that are too high"""
    assert zoom._validate_ratio(501, "test") is False
    assert zoom._validate_ratio(1000, "test") is False


def test_validate_ratio_none(zoom):
    """Test validation rejects None"""
    assert zoom._validate_ratio(None, "test") is False


def test_validate_ratio_invalid_type(zoom):
    """Test validation rejects invalid types"""
    assert zoom._validate_ratio("177", "test") is False
    assert zoom._validate_ratio([177], "test") is False
    assert zoom._validate_ratio({"ratio": 177}, "test") is False


def test_calculate_zoom_invalid_ratio_returns_1(zoom):
    """Test that invalid ratios return zoom of 1.0"""
    assert zoom._calculate_zoom(99) == 1.0  # Too low
    assert zoom._calculate_zoom(501) == 1.0  # Too high
    assert zoom._calculate_zoom(None) == 1.0  # None


def test_calculate_zoom_invalid_file_ratio_ignored(zoom):
    """Test that invalid file_ratio is ignored"""
    # Valid detected_ratio, invalid file_ratio
    zoom_value = zoom._calculate_zoom(235, file_ratio=99)
    # Should use detected_ratio normally
    expected = 235 / 177.0
    assert abs(zoom_value - expected) < 0.01

