"""
Tests pour IMDbProvider.
Note: Ces tests mockent getOriginalAspectRatio() car on ne veut pas faire
de vraies requêtes HTTP dans les tests unitaires.
"""
import unittest
import sys
import os

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


class TestIMDbProvider(unittest.TestCase):
    """Tests pour IMDbProvider"""
    
    def setUp(self):
        """Initialiser le provider"""
        self.provider = IMDbProvider()
    
    def tearDown(self):
        """Nettoyage après test"""
        pass
    
    def test_get_aspect_ratio_with_imdb_number(self):
        """Test avec IMDb number"""
        # Patcher getOriginalAspectRatio dans le module addon
        original_func = addon_module.getOriginalAspectRatio
        addon_module.getOriginalAspectRatio = mock_get_original_aspect_ratio
        try:
            ratio = self.provider.get_aspect_ratio("Any Title", imdb_number="tt1234567")
            self.assertEqual(ratio, 235)
        finally:
            addon_module.getOriginalAspectRatio = original_func
    
    def test_get_aspect_ratio_with_title(self):
        """Test avec titre"""
        # Patcher getOriginalAspectRatio dans le module addon
        original_func = addon_module.getOriginalAspectRatio
        addon_module.getOriginalAspectRatio = mock_get_original_aspect_ratio
        try:
            ratio = self.provider.get_aspect_ratio("Test Movie")
            self.assertEqual(ratio, 200)
        finally:
            addon_module.getOriginalAspectRatio = original_func
    
    def test_get_aspect_ratio_multiple_ratios(self):
        """Test avec plusieurs ratios (devrait prendre le premier)"""
        # Patcher getOriginalAspectRatio dans le module addon
        original_func = addon_module.getOriginalAspectRatio
        addon_module.getOriginalAspectRatio = mock_get_original_aspect_ratio
        try:
            ratio = self.provider.get_aspect_ratio("Multiple Ratios")
            self.assertEqual(ratio, 185)  # Premier de la liste
        finally:
            addon_module.getOriginalAspectRatio = original_func
    
    def test_get_aspect_ratio_not_found(self):
        """Test quand aucun ratio n'est trouvé"""
        ratio = self.provider.get_aspect_ratio("Error Movie")
        self.assertIsNone(ratio)
    
    def test_get_aspect_ratio_none_title(self):
        """Test avec titre None"""
        ratio = self.provider.get_aspect_ratio(None)
        self.assertIsNone(ratio)
    
    def test_get_aspect_ratio_empty_title(self):
        """Test avec titre vide"""
        ratio = self.provider.get_aspect_ratio("")
        self.assertIsNone(ratio)
    
    def test_error_handling(self):
        """Test gestion d'erreur (si getOriginalAspectRatio lève une exception)"""
        def failing_mock(title, imdb_number=None):
            raise Exception("Network error")
        
        # Patcher getOriginalAspectRatio dans le module addon
        original_func = addon_module.getOriginalAspectRatio
        addon_module.getOriginalAspectRatio = failing_mock
        try:
            ratio = self.provider.get_aspect_ratio("Test Movie")
            self.assertIsNone(ratio)
        finally:
            addon_module.getOriginalAspectRatio = original_func


if __name__ == "__main__":
    unittest.main()

