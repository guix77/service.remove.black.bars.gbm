"""
Tests pour KodiMetadataProvider.
"""
import sys
import os
import pytest

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
from tests.mock_kodi import MockVideoInfoTag


@pytest.fixture
def provider():
    """Fixture pour créer un provider"""
    provider = KodiMetadataProvider()
    import xbmc
    xbmc.info_label = mock_kodi.MockInfoLabel()
    return provider


def test_get_aspect_ratio_from_info_label(provider):
    """Test avec VideoPlayer.VideoAspect InfoLabel"""
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_getInfoLabel = addon_module.xbmc.getInfoLabel
    addon_module.xbmc.getInfoLabel = lambda label: "2.35" if label == "VideoPlayer.VideoAspect" else ""
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio == 235
    finally:
        addon_module.xbmc.getInfoLabel = original_getInfoLabel


def test_get_aspect_ratio_16_9(provider):
    """Test avec ratio 16:9"""
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_getInfoLabel = addon_module.xbmc.getInfoLabel
    addon_module.xbmc.getInfoLabel = lambda label: "1.78" if label == "VideoPlayer.VideoAspect" else ""
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio == 178
    finally:
        addon_module.xbmc.getInfoLabel = original_getInfoLabel


def test_get_aspect_ratio_4_3(provider):
    """Test avec ratio 4:3"""
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_getInfoLabel = addon_module.xbmc.getInfoLabel
    addon_module.xbmc.getInfoLabel = lambda label: "1.33" if label == "VideoPlayer.VideoAspect" else ""
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio == 133
    finally:
        addon_module.xbmc.getInfoLabel = original_getInfoLabel


def test_info_label_with_ar_suffix(provider):
    """Test avec format '2.35AR'"""
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_getInfoLabel = addon_module.xbmc.getInfoLabel
    addon_module.xbmc.getInfoLabel = lambda label: "1.85AR" if label == "VideoPlayer.VideoAspect" else ""
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio == 185
    finally:
        addon_module.xbmc.getInfoLabel = original_getInfoLabel


def test_info_label_with_colon(provider):
    """Test avec format '1.85:1'"""
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_getInfoLabel = addon_module.xbmc.getInfoLabel
    addon_module.xbmc.getInfoLabel = lambda label: "1.85:1" if label == "VideoPlayer.VideoAspect" else ""
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio == 185
    finally:
        addon_module.xbmc.getInfoLabel = original_getInfoLabel


def test_no_aspect_ratio_available(provider):
    """Test quand aucun ratio n'est disponible"""
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_getInfoLabel = addon_module.xbmc.getInfoLabel
    addon_module.xbmc.getInfoLabel = lambda label: "" if label == "VideoPlayer.VideoAspect" else ""
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio is None
    finally:
        addon_module.xbmc.getInfoLabel = original_getInfoLabel


def test_label_returns_itself(provider):
    """Test quand getInfoLabel retourne le nom du label (non disponible)"""
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_getInfoLabel = addon_module.xbmc.getInfoLabel
    addon_module.xbmc.getInfoLabel = lambda label: "VideoPlayer.VideoAspect" if label == "VideoPlayer.VideoAspect" else ""
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio is None
    finally:
        addon_module.xbmc.getInfoLabel = original_getInfoLabel


def test_rounding(provider):
    """Test arrondi correct (2.355 -> 236)"""
    video_tag = MockVideoInfoTag()
    import addon as addon_module
    original_getInfoLabel = addon_module.xbmc.getInfoLabel
    addon_module.xbmc.getInfoLabel = lambda label: "2.355" if label == "VideoPlayer.VideoAspect" else ""
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio == int((2.355 + 0.005) * 100)
    finally:
        addon_module.xbmc.getInfoLabel = original_getInfoLabel


def test_with_remote_source(provider):
    """Test avec source distante (Jellyfin/Plex)"""
    video_tag = MockVideoInfoTag(filename="http://jellyfin/video.mp4")
    import addon as addon_module
    original_getInfoLabel = addon_module.xbmc.getInfoLabel
    addon_module.xbmc.getInfoLabel = lambda label: "2.40" if label == "VideoPlayer.VideoAspect" else ""
    try:
        ratio = provider.get_aspect_ratio(video_tag)
        assert ratio == 240
    finally:
        addon_module.xbmc.getInfoLabel = original_getInfoLabel
