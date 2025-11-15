"""
Tests pour JsonCacheProvider.
"""
import sys
import os
import json
import tempfile
import shutil
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

from addon import JsonCacheProvider, translate_profile_path
from tests.mock_kodi import MockAddon


@pytest.fixture
def temp_cache():
    """Fixture pour créer un cache temporaire"""
    temp_dir = tempfile.mkdtemp()
    # Mocker translate_profile_path pour utiliser le temp_dir
    import xbmcaddon
    xbmcaddon.Addon = lambda: MockAddon(profile_path=temp_dir)
    
    # Créer le provider
    cache = JsonCacheProvider()
    cache.path = os.path.join(temp_dir, "cache.json")
    cache._cache = {}
    
    yield cache
    
    # Nettoyer
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_store_and_get(temp_cache):
    """Test stockage et récupération basique"""
    temp_cache.store("Test Movie", 2020, 235)
    ratio = temp_cache.get("Test Movie", 2020)
    assert ratio == 235


def test_store_with_year(temp_cache):
    """Test avec année"""
    temp_cache.store("Test Movie", 2020, 200)
    ratio = temp_cache.get("Test Movie", 2020)
    assert ratio == 200


def test_store_without_year(temp_cache):
    """Test sans année"""
    temp_cache.store("Test Movie", None, 185)
    ratio = temp_cache.get("Test Movie", None)
    assert ratio == 185


def test_get_nonexistent(temp_cache):
    """Test récupération d'une clé inexistante"""
    ratio = temp_cache.get("Nonexistent Movie", 2020)
    assert ratio is None


def test_store_with_imdb_id(temp_cache):
    """Test avec IMDb ID"""
    temp_cache.store("Test Movie", 2020, 240, imdb_id="tt1234567")
    ratio = temp_cache.get("Test Movie", 2020, imdb_id="tt1234567")
    assert ratio == 240


def test_imdb_id_priority(temp_cache):
    """Test que IMDb ID a priorité sur title+year"""
    temp_cache.store("Test Movie", 2020, 235, imdb_id="tt1234567")
    # Devrait trouver même avec title différent
    ratio = temp_cache.get("Different Title", 2021, imdb_id="tt1234567")
    assert ratio == 235


def test_case_insensitive_title(temp_cache):
    """Test que les titres sont case-insensitive (normalisés en lowercase)"""
    temp_cache.store("Test Movie", 2020, 200)
    ratio = temp_cache.get("test movie", 2020)
    assert ratio == 200


def test_persistence(temp_cache):
    """Test persistance du cache"""
    temp_cache.store("Test Movie", 2020, 235)
    temp_cache._save()
    
    # Créer un nouveau provider qui charge le cache
    new_cache = JsonCacheProvider()
    new_cache.path = temp_cache.path
    new_cache._cache = new_cache._load()
    
    ratio = new_cache.get("Test Movie", 2020)
    assert ratio == 235


def test_multiple_movies(temp_cache):
    """Test avec plusieurs films"""
    temp_cache.store("Movie 1", 2020, 185)
    temp_cache.store("Movie 2", 2021, 200)
    temp_cache.store("Movie 3", 2022, 235)
    
    assert temp_cache.get("Movie 1", 2020) == 185
    assert temp_cache.get("Movie 2", 2021) == 200
    assert temp_cache.get("Movie 3", 2022) == 235


def test_overwrite_existing(temp_cache):
    """Test écrasement d'une valeur existante"""
    temp_cache.store("Test Movie", 2020, 185)
    temp_cache.store("Test Movie", 2020, 235)  # Overwrite
    ratio = temp_cache.get("Test Movie", 2020)
    assert ratio == 235
