"""
Tests pour JsonCacheProvider.
"""
import unittest
import sys
import os
import json
import tempfile
import shutil

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


class TestJsonCacheProvider(unittest.TestCase):
    """Tests pour JsonCacheProvider"""
    
    def setUp(self):
        """Créer un répertoire temporaire pour le cache"""
        self.temp_dir = tempfile.mkdtemp()
        # Mocker translate_profile_path pour utiliser le temp_dir
        import xbmcaddon
        xbmcaddon.Addon = lambda: MockAddon(profile_path=self.temp_dir)
        
        # Réinitialiser le provider
        self.cache = JsonCacheProvider()
        self.cache.path = os.path.join(self.temp_dir, "cache.json")
        self.cache._cache = {}
    
    def tearDown(self):
        """Nettoyer les fichiers temporaires"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_store_and_get(self):
        """Test stockage et récupération basique"""
        self.cache.store("Test Movie", 2020, 235)
        ratio = self.cache.get("Test Movie", 2020)
        self.assertEqual(ratio, 235)
    
    def test_store_with_year(self):
        """Test avec année"""
        self.cache.store("Test Movie", 2020, 200)
        ratio = self.cache.get("Test Movie", 2020)
        self.assertEqual(ratio, 200)
    
    def test_store_without_year(self):
        """Test sans année"""
        self.cache.store("Test Movie", None, 185)
        ratio = self.cache.get("Test Movie", None)
        self.assertEqual(ratio, 185)
    
    def test_get_nonexistent(self):
        """Test récupération d'une clé inexistante"""
        ratio = self.cache.get("Nonexistent Movie", 2020)
        self.assertIsNone(ratio)
    
    def test_store_with_imdb_id(self):
        """Test avec IMDb ID"""
        self.cache.store("Test Movie", 2020, 240, imdb_id="tt1234567")
        ratio = self.cache.get("Test Movie", 2020, imdb_id="tt1234567")
        self.assertEqual(ratio, 240)
    
    def test_imdb_id_priority(self):
        """Test que IMDb ID a priorité sur title+year"""
        self.cache.store("Test Movie", 2020, 235, imdb_id="tt1234567")
        # Devrait trouver même avec title différent
        ratio = self.cache.get("Different Title", 2021, imdb_id="tt1234567")
        self.assertEqual(ratio, 235)
    
    def test_case_insensitive_title(self):
        """Test que les titres sont case-insensitive (normalisés en lowercase)"""
        self.cache.store("Test Movie", 2020, 200)
        ratio = self.cache.get("test movie", 2020)
        self.assertEqual(ratio, 200)
    
    def test_persistence(self):
        """Test persistance du cache"""
        self.cache.store("Test Movie", 2020, 235)
        self.cache._save()
        
        # Créer un nouveau provider qui charge le cache
        new_cache = JsonCacheProvider()
        new_cache.path = self.cache.path
        new_cache._cache = new_cache._load()
        
        ratio = new_cache.get("Test Movie", 2020)
        self.assertEqual(ratio, 235)
    
    def test_multiple_movies(self):
        """Test avec plusieurs films"""
        self.cache.store("Movie 1", 2020, 185)
        self.cache.store("Movie 2", 2021, 200)
        self.cache.store("Movie 3", 2022, 235)
        
        self.assertEqual(self.cache.get("Movie 1", 2020), 185)
        self.assertEqual(self.cache.get("Movie 2", 2021), 200)
        self.assertEqual(self.cache.get("Movie 3", 2022), 235)
    
    def test_overwrite_existing(self):
        """Test écrasement d'une valeur existante"""
        self.cache.store("Test Movie", 2020, 185)
        self.cache.store("Test Movie", 2020, 235)  # Overwrite
        ratio = self.cache.get("Test Movie", 2020)
        self.assertEqual(ratio, 235)


if __name__ == "__main__":
    unittest.main()

