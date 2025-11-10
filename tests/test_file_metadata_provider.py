"""
Tests pour FileMetadataProvider.
"""
import unittest
import sys
import os
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

from addon import FileMetadataProvider


class TestFileMetadataProvider(unittest.TestCase):
    """Tests pour FileMetadataProvider"""
    
    def setUp(self):
        """Créer un fichier temporaire pour les tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test.mp4")
        with open(self.temp_file, "w") as f:
            f.write("test")
        self.provider = FileMetadataProvider()
    
    def tearDown(self):
        """Nettoyer les fichiers temporaires"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_is_local_file_with_local_file(self):
        """Test is_local_file() avec fichier local"""
        self.assertTrue(self.provider.is_local_file(self.temp_file))
    
    def test_is_local_file_with_nonexistent(self):
        """Test is_local_file() avec fichier inexistant"""
        fake_path = os.path.join(self.temp_dir, "nonexistent.mp4")
        self.assertFalse(self.provider.is_local_file(fake_path))
    
    def test_is_local_file_with_http(self):
        """Test is_local_file() avec URL HTTP"""
        self.assertFalse(self.provider.is_local_file("http://example.com/video.mp4"))
    
    def test_is_local_file_with_https(self):
        """Test is_local_file() avec URL HTTPS"""
        self.assertFalse(self.provider.is_local_file("https://example.com/video.mp4"))
    
    def test_is_local_file_with_smb(self):
        """Test is_local_file() avec URL SMB"""
        self.assertFalse(self.provider.is_local_file("smb://server/share/video.mp4"))
    
    def test_is_local_file_with_nfs(self):
        """Test is_local_file() avec URL NFS"""
        self.assertFalse(self.provider.is_local_file("nfs://server/path/video.mp4"))
    
    def test_is_local_file_with_ftp(self):
        """Test is_local_file() avec URL FTP"""
        self.assertFalse(self.provider.is_local_file("ftp://server/path/video.mp4"))
    
    def test_is_local_file_with_empty(self):
        """Test is_local_file() avec chemin vide"""
        self.assertFalse(self.provider.is_local_file(""))
        self.assertFalse(self.provider.is_local_file(None))
    
    def test_extract_from_file_returns_none(self):
        """Test extract_from_file() retourne None (non implémenté pour GBM)"""
        # Selon SPEC, extract_from_file() retourne None pour garder GBM simple
        ratio = self.provider.extract_from_file(self.temp_file)
        self.assertIsNone(ratio)
    
    def test_skip_network_file(self):
        """Test que les fichiers réseau sont détectés et ignorés"""
        network_path = "http://jellyfin.example.com/video.mp4"
        self.assertFalse(self.provider.is_local_file(network_path))
        # extract_from_file() ne devrait pas être appelé pour fichiers réseau
        ratio = self.provider.extract_from_file(network_path)
        self.assertIsNone(ratio)


if __name__ == "__main__":
    unittest.main()

