"""
Tests pour ZoomApplier.
"""
import unittest
import sys
import os
import time

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


class TestZoomApplier(unittest.TestCase):
    """Tests pour ZoomApplier"""
    
    def setUp(self):
        """Initialiser ZoomApplier"""
        self.zoom = ZoomApplier()
        self.mock_player = MockPlayer(is_playing_video=True, is_playing=True)
        # Mocker xbmcgui pour retourner window_id 12005 (fullscreen)
        import xbmcgui
        xbmcgui.getCurrentWindowId = lambda: 12005
        # Mocker xbmc.executeJSONRPC
        import xbmc
        xbmc.executeJSONRPC = lambda cmd: None
    
    def test_calculate_zoom_ratio_235(self):
        """Test calcul zoom pour ratio 235 (2.35:1)"""
        zoom = self.zoom._calculate_zoom(235)
        expected = 235 / 177.0
        self.assertAlmostEqual(zoom, expected, places=2)
    
    def test_calculate_zoom_ratio_200(self):
        """Test calcul zoom pour ratio 200 (2.00:1)"""
        zoom = self.zoom._calculate_zoom(200)
        expected = 200 / 177.0
        self.assertAlmostEqual(zoom, expected, places=2)
    
    def test_calculate_zoom_ratio_185(self):
        """Test calcul zoom pour ratio 185 (1.85:1)"""
        zoom = self.zoom._calculate_zoom(185)
        expected = 185 / 177.0
        self.assertAlmostEqual(zoom, expected, places=2)
    
    def test_calculate_zoom_ratio_177(self):
        """Test calcul zoom pour ratio 177 (16:9) - pas de zoom"""
        zoom = self.zoom._calculate_zoom(177)
        self.assertEqual(zoom, 1.0)
    
    def test_calculate_zoom_ratio_133(self):
        """Test calcul zoom pour ratio 133 (4:3) - pas de zoom"""
        zoom = self.zoom._calculate_zoom(133)
        self.assertEqual(zoom, 1.0)
    
    def test_calculate_zoom_ratio_240(self):
        """Test calcul zoom pour ratio 240 (2.40:1)"""
        zoom = self.zoom._calculate_zoom(240)
        expected = 240 / 177.0
        self.assertAlmostEqual(zoom, expected, places=2)
    
    def test_no_zoom_if_ratio_less_than_177(self):
        """Test qu'il n'y a pas de zoom si ratio <= 177"""
        for ratio in [133, 177]:
            zoom = self.zoom._calculate_zoom(ratio)
            self.assertEqual(zoom, 1.0)
    
    def test_rate_limiting(self):
        """Test rate limiting (500ms)"""
        # Premier zoom devrait fonctionner
        result1 = self.zoom.apply_zoom(235, self.mock_player)
        self.assertTrue(result1)
        
        # Deuxième zoom immédiatement après devrait être bloqué
        result2 = self.zoom.apply_zoom(240, self.mock_player)
        self.assertFalse(result2)
        
        # Attendre plus de 500ms
        time.sleep(0.6)
        result3 = self.zoom.apply_zoom(240, self.mock_player)
        self.assertTrue(result3)
    
    def test_no_zoom_if_not_playing_video(self):
        """Test qu'il n'y a pas de zoom si vidéo ne joue pas"""
        not_playing_player = MockPlayer(is_playing_video=False, is_playing=False)
        result = self.zoom.apply_zoom(235, not_playing_player)
        self.assertFalse(result)
    
    def test_no_zoom_if_not_fullscreen(self):
        """Test qu'il n'y a pas de zoom si pas en fullscreen"""
        import addon as addon_module
        # Créer un nouveau zoom pour éviter les effets de rate limiting
        zoom = ZoomApplier()
        # Sauvegarder la fonction originale
        original_getCurrentWindowId = addon_module.xbmcgui.getCurrentWindowId
        # Mocker getCurrentWindowId pour retourner window_id non-fullscreen
        addon_module.xbmcgui.getCurrentWindowId = lambda: 10000  # Home window, pas fullscreen
        try:
            result = zoom.apply_zoom(235, self.mock_player)
            self.assertFalse(result, "Zoom ne devrait pas être appliqué si pas en fullscreen")
        finally:
            # Restaurer
            addon_module.xbmcgui.getCurrentWindowId = original_getCurrentWindowId
    
    def test_no_zoom_if_paused(self):
        """Test qu'il n'y a pas de zoom si vidéo en pause"""
        paused_player = MockPlayer(is_playing_video=True, is_playing=False)
        result = self.zoom.apply_zoom(235, paused_player)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()

