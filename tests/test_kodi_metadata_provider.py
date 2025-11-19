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
from tests.mock_kodi import MockVideoInfoTag, MockVideoStreamDetail, MockPlayer


@pytest.fixture
def provider():
    """Fixture pour créer un provider"""
    provider = KodiMetadataProvider()
    import xbmc
    xbmc.info_label = mock_kodi.MockInfoLabel()
    return provider


def test_get_aspect_ratio_from_python_api(provider):
    """Test avec Python API pour ratio 2.35:1 (1920x816)"""
    video_tag = MockVideoInfoTag()
    stream_detail = MockVideoStreamDetail(width=1920, height=816)
    video_info_tag = MockVideoInfoTag(video_stream_detail=stream_detail)
    player = MockPlayer(video_info_tag=video_info_tag)
    
    ratio = provider.get_aspect_ratio(video_tag, player=player)
    assert ratio == 235


def test_get_aspect_ratio_16_9(provider):
    """Test avec ratio 16:9 (1920x1080)"""
    video_tag = MockVideoInfoTag()
    stream_detail = MockVideoStreamDetail(width=1920, height=1080)
    video_info_tag = MockVideoInfoTag(video_stream_detail=stream_detail)
    player = MockPlayer(video_info_tag=video_info_tag)
    
    ratio = provider.get_aspect_ratio(video_tag, player=player)
    # 1920/1080 = 1.777... * 100 = 177.7... arrondi = 177
    assert ratio == 177


def test_get_aspect_ratio_4_3(provider):
    """Test avec ratio 4:3 (1440x1080)"""
    video_tag = MockVideoInfoTag()
    stream_detail = MockVideoStreamDetail(width=1440, height=1080)
    video_info_tag = MockVideoInfoTag(video_stream_detail=stream_detail)
    player = MockPlayer(video_info_tag=video_info_tag)
    
    ratio = provider.get_aspect_ratio(video_tag, player=player)
    assert ratio == 133


def test_get_aspect_ratio_1_85(provider):
    """Test avec ratio 1.85:1 (1920x1037)"""
    video_tag = MockVideoInfoTag()
    stream_detail = MockVideoStreamDetail(width=1920, height=1037)
    video_info_tag = MockVideoInfoTag(video_stream_detail=stream_detail)
    player = MockPlayer(video_info_tag=video_info_tag)
    
    ratio = provider.get_aspect_ratio(video_tag, player=player)
    # 1920/1037 = 1.851... * 100 = 185.1... arrondi = 185
    assert ratio == 185


def test_get_aspect_ratio_2_40(provider):
    """Test avec ratio 2.40:1 (1920x800)"""
    video_tag = MockVideoInfoTag()
    stream_detail = MockVideoStreamDetail(width=1920, height=800)
    video_info_tag = MockVideoInfoTag(video_stream_detail=stream_detail)
    player = MockPlayer(video_info_tag=video_info_tag)
    
    ratio = provider.get_aspect_ratio(video_tag, player=player)
    assert ratio == 240


def test_no_aspect_ratio_available(provider):
    """Test quand aucun ratio n'est disponible (getVideoStreamDetail retourne None)"""
    video_tag = MockVideoInfoTag()
    video_info_tag = MockVideoInfoTag(video_stream_detail=None)  # Pas de stream detail
    player = MockPlayer(video_info_tag=video_info_tag)
    
    ratio = provider.get_aspect_ratio(video_tag, player=player)
    assert ratio is None


def test_no_player_provided(provider):
    """Test quand aucun player n'est fourni"""
    video_tag = MockVideoInfoTag()
    
    ratio = provider.get_aspect_ratio(video_tag, player=None)
    assert ratio is None


def test_rounding(provider):
    """Test arrondi correct (1920x813 ≈ 2.36:1 -> 236)"""
    video_tag = MockVideoInfoTag()
    stream_detail = MockVideoStreamDetail(width=1920, height=813)
    video_info_tag = MockVideoInfoTag(video_stream_detail=stream_detail)
    player = MockPlayer(video_info_tag=video_info_tag)
    
    ratio = provider.get_aspect_ratio(video_tag, player=player)
    # 1920/813 = 2.361... * 100 = 236.1... arrondi = 236
    assert ratio == 236


def test_with_remote_source(provider):
    """Test avec source distante (Jellyfin/Plex)"""
    video_tag = MockVideoInfoTag(filename="http://jellyfin/video.mp4")
    stream_detail = MockVideoStreamDetail(width=1920, height=800)
    video_info_tag = MockVideoInfoTag(video_stream_detail=stream_detail)
    player = MockPlayer(video_info_tag=video_info_tag)
    
    ratio = provider.get_aspect_ratio(video_tag, player=player)
    assert ratio == 240


def test_get_aspect_ratio_from_resolution(provider):
    """Test calcul depuis résolution réelle via Python API (plus précis)"""
    video_tag = MockVideoInfoTag()
    stream_detail = MockVideoStreamDetail(width=576, height=352)
    video_info_tag = MockVideoInfoTag(video_stream_detail=stream_detail)
    player = MockPlayer(video_info_tag=video_info_tag)
    
    ratio = provider.get_aspect_ratio(video_tag, player=player)
    # 576/352 = 1.6364, * 100 = 163.64, arrondi = 163
    expected = int((576 / 352.0) * 100)
    assert ratio == expected, f"Expected {expected}, got {ratio}"


def test_resolution_from_python_api(provider):
    """Test que la résolution via Python API fonctionne correctement"""
    video_tag = MockVideoInfoTag()
    stream_detail = MockVideoStreamDetail(width=576, height=352)
    video_info_tag = MockVideoInfoTag(video_stream_detail=stream_detail)
    player = MockPlayer(video_info_tag=video_info_tag)
    
    ratio = provider.get_aspect_ratio(video_tag, player=player)
    # Devrait utiliser la résolution (163)
    expected_from_resolution = int((576 / 352.0) * 100)
    assert ratio == expected_from_resolution, f"Should use resolution ({expected_from_resolution}). Got {ratio}"
