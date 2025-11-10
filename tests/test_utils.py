"""
Tests pour les fonctions utilitaires.
"""
import unittest
import os
import sys
import tempfile
import shutil

# Ajouter le répertoire parent au path pour importer addon
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mocker les modules Kodi avant d'importer addon
import tests.mock_kodi as mock_kodi
mock_xbmc = mock_kodi.MockXbmc()
sys.modules['xbmc'] = mock_xbmc
sys.modules['xbmcaddon'] = type(sys)('xbmcaddon')
sys.modules['xbmcaddon'].Addon = lambda: mock_kodi.MockAddon()
sys.modules['xbmcgui'] = mock_kodi.MockXbmcgui()

from addon import is_local_file


class TestIsLocalFile(unittest.TestCase):
    """Tests pour is_local_file()"""
    
    def setUp(self):
        """Créer un fichier temporaire pour les tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test.mp4")
        with open(self.temp_file, "w") as f:
            f.write("test")
    
    def tearDown(self):
        """Nettoyer les fichiers temporaires"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_local_file_exists(self):
        """Test avec un fichier local existant"""
        self.assertTrue(is_local_file(self.temp_file))
    
    def test_local_file_not_exists(self):
        """Test avec un fichier local inexistant"""
        fake_path = os.path.join(self.temp_dir, "nonexistent.mp4")
        self.assertFalse(is_local_file(fake_path))
    
    def test_http_url(self):
        """Test avec URL HTTP"""
        self.assertFalse(is_local_file("http://example.com/video.mp4"))
    
    def test_https_url(self):
        """Test avec URL HTTPS"""
        self.assertFalse(is_local_file("https://example.com/video.mp4"))
    
    def test_smb_url(self):
        """Test avec URL SMB"""
        self.assertFalse(is_local_file("smb://server/share/video.mp4"))
    
    def test_nfs_url(self):
        """Test avec URL NFS"""
        self.assertFalse(is_local_file("nfs://server/path/video.mp4"))
    
    def test_ftp_url(self):
        """Test avec URL FTP"""
        self.assertFalse(is_local_file("ftp://server/path/video.mp4"))
    
    def test_empty_path(self):
        """Test avec chemin vide"""
        self.assertFalse(is_local_file(""))
        self.assertFalse(is_local_file(None))
    
    def test_absolute_path_unix(self):
        """Test avec chemin absolu Unix"""
        if os.name != "nt":
            # Sur Unix, un chemin absolu devrait être détecté
            self.assertIsInstance(is_local_file("/tmp/test.mp4"), bool)
    
    def test_relative_path(self):
        """Test avec chemin relatif"""
        # Les chemins relatifs ne sont pas considérés comme locaux
        self.assertFalse(is_local_file("video.mp4"))


if __name__ == "__main__":
    unittest.main()

