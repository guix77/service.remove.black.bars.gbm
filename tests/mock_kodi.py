"""
Mock Kodi pour tests unitaires.
Simule les modules xbmc, xbmcaddon, xbmcgui pour permettre les tests sans Kodi.
"""


class MockInfoLabel:
    """Mock pour xbmc.getInfoLabel()"""
    def __init__(self, values=None):
        self.values = values or {}
    
    def get(self, label):
        return self.values.get(label, "")


class MockVideoInfoTag:
    """Mock pour video_info_tag"""
    def __init__(self, aspect_ratio=None, media_type="movie", title=None, 
                 original_title=None, year=None, tvshow_title=None, filename=None):
        self._aspect_ratio = aspect_ratio
        self._media_type = media_type
        self._title = title
        self._original_title = original_title
        self._year = year
        self._tvshow_title = tvshow_title
        self._filename = filename
    
    def getVideoAspectRatio(self):
        return self._aspect_ratio
    
    def getMediaType(self):
        return self._media_type
    
    def getTitle(self):
        return self._title
    
    def getOriginalTitle(self):
        return self._original_title
    
    def getYear(self):
        return self._year
    
    def getTVShowTitle(self):
        return self._tvshow_title
    
    def getFilenameAndPath(self):
        return self._filename


class MockPlayer:
    """Mock pour xbmc.Player()"""
    def __init__(self, is_playing_video=False, is_playing=False):
        self._is_playing_video = is_playing_video
        self._is_playing = is_playing
    
    def isPlayingVideo(self):
        return self._is_playing_video
    
    def isPlaying(self):
        return self._is_playing
    
    def _set_zoom(self, zoom_amount):
        """Mock pour _set_zoom method"""
        return True


class MockAddon:
    """Mock pour xbmcaddon.Addon()"""
    def __init__(self, settings=None, profile_path="/tmp/test_profile"):
        self.settings = settings or {}
        self._profile_path = profile_path
    
    def getSetting(self, key):
        return self.settings.get(key, "")
    
    def getAddonInfo(self, key):
        if key == "profile":
            return self._profile_path
        return ""


class MockXbmc:
    """Mock pour module xbmc"""
    LOGDEBUG = 0
    LOGINFO = 1
    LOGWARNING = 2
    LOGERROR = 3
    
    def __init__(self, info_label_values=None):
        self.info_label = MockInfoLabel(info_label_values)
        self.logs = []
        # Player doit être une classe, pas une instance
        self.Player = MockPlayer
    
    def getInfoLabel(self, label):
        return self.info_label.get(label)
    
    def log(self, message, level=LOGINFO):
        self.logs.append((message, level))
    
    def translatePath(self, path):
        return path
    
    def executeJSONRPC(self, command):
        """Mock pour executeJSONRPC"""
        pass
    
    class Monitor:
        """Mock pour xbmc.Monitor"""
        def __init__(self):
            self._abort_requested = False
        
        def abortRequested(self):
            return self._abort_requested
        
        def waitForAbort(self, timeout):
            return False


class MockXbmcgui:
    """Mock pour module xbmcgui"""
    def __init__(self, window_id=12005):
        self._window_id = window_id
        self._window_properties = {}
        # getCurrentWindowId doit être une fonction du module, pas une méthode
        self.getCurrentWindowId = lambda: self._window_id
    
    class Window:
        def __init__(self, window_id, properties=None):
            self._properties = properties or {}
        
        def getProperty(self, key):
            return self._properties.get(key, "")
        
        def setProperty(self, key, value):
            self._properties[key] = value
    
    class Dialog:
        def notification(self, heading, message, icon=None, time=None):
            pass

