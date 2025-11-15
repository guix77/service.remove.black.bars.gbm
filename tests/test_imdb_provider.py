"""
Tests pour IMDbProvider.
Note: Ces tests mockent getOriginalAspectRatio() car on ne veut pas faire
de vraies requêtes HTTP dans les tests unitaires.
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

from addon import IMDbProvider
import addon as addon_module

# Mocker imdb.getOriginalAspectRatio après import
def mock_get_original_aspect_ratio(title, imdb_number=None):
    """Mock pour getOriginalAspectRatio"""
    # Simuler différents cas
    if imdb_number and str(imdb_number) == "tt1234567":
        return "235"
    if title and title == "Test Movie":
        return "200"
    if title and title == "Multiple Ratios":
        return ["185", "235"]  # Multiple ratios
    if title and title == "Error Movie":
        return None
    return None


@pytest.fixture
def provider():
    """Fixture pour créer un provider"""
    return IMDbProvider()


def test_get_aspect_ratio_with_imdb_number(provider):
    """Test avec IMDb number"""
    # Patcher getOriginalAspectRatio dans le module addon
    original_func = addon_module.getOriginalAspectRatio
    addon_module.getOriginalAspectRatio = mock_get_original_aspect_ratio
    try:
        ratio = provider.get_aspect_ratio("Any Title", imdb_number="tt1234567")
        assert ratio == 235
    finally:
        addon_module.getOriginalAspectRatio = original_func


def test_get_aspect_ratio_with_title(provider):
    """Test avec titre"""
    # Patcher getOriginalAspectRatio dans le module addon
    original_func = addon_module.getOriginalAspectRatio
    addon_module.getOriginalAspectRatio = mock_get_original_aspect_ratio
    try:
        ratio = provider.get_aspect_ratio("Test Movie")
        assert ratio == 200
    finally:
        addon_module.getOriginalAspectRatio = original_func


def test_get_aspect_ratio_multiple_ratios(provider):
    """Test avec plusieurs ratios (devrait prendre le premier)"""
    # Patcher getOriginalAspectRatio dans le module addon
    original_func = addon_module.getOriginalAspectRatio
    addon_module.getOriginalAspectRatio = mock_get_original_aspect_ratio
    try:
        ratio = provider.get_aspect_ratio("Multiple Ratios")
        assert ratio == 185  # Premier de la liste
    finally:
        addon_module.getOriginalAspectRatio = original_func


def test_get_aspect_ratio_not_found(provider):
    """Test quand aucun ratio n'est trouvé"""
    ratio = provider.get_aspect_ratio("Error Movie")
    assert ratio is None


def test_get_aspect_ratio_none_title(provider):
    """Test avec titre None"""
    ratio = provider.get_aspect_ratio(None)
    assert ratio is None


def test_get_aspect_ratio_empty_title(provider):
    """Test avec titre vide"""
    ratio = provider.get_aspect_ratio("")
    assert ratio is None


def test_error_handling(provider):
    """Test gestion d'erreur (si getOriginalAspectRatio lève une exception)"""
    def failing_mock(title, imdb_number=None):
        raise Exception("Network error")
    
    # Patcher getOriginalAspectRatio dans le module addon
    original_func = addon_module.getOriginalAspectRatio
    addon_module.getOriginalAspectRatio = failing_mock
    try:
        ratio = provider.get_aspect_ratio("Test Movie")
        assert ratio is None
    finally:
        addon_module.getOriginalAspectRatio = original_func
