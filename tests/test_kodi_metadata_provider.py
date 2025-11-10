"""
Tests pour KodiMetadataProvider.
"""
import unittest
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mocker les modules Kodi avant d'importer addon
import tests.mock_kodi as mock_kodi
mock_xbmc = mock_kodi.MockXbmc()
sys.modules['xbmc'] = mock_xbmc
sys.modules['xbmcaddon'] = type(sys)('xbmcaddon')
sys.modules['xbmcaddon'].Addon = lambda: mock_kodi.MockAddon()
sys.modules['xbmcgui'] = mock_kodi.MockXbmcgui()

from addon import KodiMetadataProvider
from tests.mock_kodi import MockVideoInfoTag, MockXbmc


class TestKodiMetadataProvider(unittest.TestCase):
    """Tests pour KodiMetadataProvider"""
    
    def setUp(self):
        """Initialiser le provider"""
        self.provider = KodiMetadataProvider()
        import xbmc
        xbmc.info_label = mock_kodi.MockInfoLabel()
    
    def test_get_aspect_ratio_from_info_label(self):
        """Test avec VideoPlayer.VideoAspect InfoLabel"""
        video_tag = MockVideoInfoTag()
        import xbmc
        import addon as addon_module
        original_getInfoLabel = addon_module.xbmc.getInfoLabel
        addon_module.xbmc.getInfoLabel = lambda label: "2.35" if label == "VideoPlayer.VideoAspect" else ""
        ratio = self.provider.get_aspect_ratio(video_tag)
        addon_module.xbmc.getInfoLabel = original_getInfoLabel
        self.assertEqual(ratio, 235)
    
    def test_get_aspect_ratio_16_9(self):
        """Test avec ratio 16:9"""
        video_tag = MockVideoInfoTag()
        import addon as addon_module
        original_getInfoLabel = addon_module.xbmc.getInfoLabel
        addon_module.xbmc.getInfoLabel = lambda label: "1.78" if label == "VideoPlayer.VideoAspect" else ""
        ratio = self.provider.get_aspect_ratio(video_tag)
        addon_module.xbmc.getInfoLabel = original_getInfoLabel
        self.assertEqual(ratio, 178)
    
    def test_get_aspect_ratio_4_3(self):
        """Test avec ratio 4:3"""
        video_tag = MockVideoInfoTag()
        import addon as addon_module
        original_getInfoLabel = addon_module.xbmc.getInfoLabel
        addon_module.xbmc.getInfoLabel = lambda label: "1.33" if label == "VideoPlayer.VideoAspect" else ""
        ratio = self.provider.get_aspect_ratio(video_tag)
        addon_module.xbmc.getInfoLabel = original_getInfoLabel
        self.assertEqual(ratio, 133)
    
    def test_info_label_with_ar_suffix(self):
        """Test avec format '2.35AR'"""
        video_tag = MockVideoInfoTag()
        import addon as addon_module
        original_getInfoLabel = addon_module.xbmc.getInfoLabel
        addon_module.xbmc.getInfoLabel = lambda label: "1.85AR" if label == "VideoPlayer.VideoAspect" else ""
        ratio = self.provider.get_aspect_ratio(video_tag)
        addon_module.xbmc.getInfoLabel = original_getInfoLabel
        self.assertEqual(ratio, 185)
    
    def test_info_label_with_colon(self):
        """Test avec format '1.85:1'"""
        video_tag = MockVideoInfoTag()
        import addon as addon_module
        original_getInfoLabel = addon_module.xbmc.getInfoLabel
        addon_module.xbmc.getInfoLabel = lambda label: "1.85:1" if label == "VideoPlayer.VideoAspect" else ""
        ratio = self.provider.get_aspect_ratio(video_tag)
        addon_module.xbmc.getInfoLabel = original_getInfoLabel
        self.assertEqual(ratio, 185)
    
    def test_no_aspect_ratio_available(self):
        """Test quand aucun ratio n'est disponible"""
        video_tag = MockVideoInfoTag()
        import addon as addon_module
        original_getInfoLabel = addon_module.xbmc.getInfoLabel
        addon_module.xbmc.getInfoLabel = lambda label: "" if label == "VideoPlayer.VideoAspect" else ""
        ratio = self.provider.get_aspect_ratio(video_tag)
        addon_module.xbmc.getInfoLabel = original_getInfoLabel
        self.assertIsNone(ratio)
    
    def test_label_returns_itself(self):
        """Test quand getInfoLabel retourne le nom du label (non disponible)"""
        video_tag = MockVideoInfoTag()
        import addon as addon_module
        original_getInfoLabel = addon_module.xbmc.getInfoLabel
        addon_module.xbmc.getInfoLabel = lambda label: "VideoPlayer.VideoAspect" if label == "VideoPlayer.VideoAspect" else ""
        ratio = self.provider.get_aspect_ratio(video_tag)
        addon_module.xbmc.getInfoLabel = original_getInfoLabel
        self.assertIsNone(ratio)
    
    def test_rounding(self):
        """Test arrondi correct (2.355 -> 236)"""
        video_tag = MockVideoInfoTag()
        import addon as addon_module
        original_getInfoLabel = addon_module.xbmc.getInfoLabel
        addon_module.xbmc.getInfoLabel = lambda label: "2.355" if label == "VideoPlayer.VideoAspect" else ""
        ratio = self.provider.get_aspect_ratio(video_tag)
        addon_module.xbmc.getInfoLabel = original_getInfoLabel
        self.assertEqual(ratio, int((2.355 + 0.005) * 100))
    
    def test_with_remote_source(self):
        """Test avec source distante (Jellyfin/Plex)"""
        video_tag = MockVideoInfoTag(filename="http://jellyfin/video.mp4")
        import addon as addon_module
        original_getInfoLabel = addon_module.xbmc.getInfoLabel
        addon_module.xbmc.getInfoLabel = lambda label: "2.40" if label == "VideoPlayer.VideoAspect" else ""
        ratio = self.provider.get_aspect_ratio(video_tag)
        addon_module.xbmc.getInfoLabel = original_getInfoLabel
        self.assertEqual(ratio, 240)


if __name__ == "__main__":
    unittest.main()

