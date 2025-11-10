import os
import sys
import json
import time

import xbmc
import xbmcaddon
import xbmcgui

try:
    import xbmcvfs
    translatePath = xbmcvfs.translatePath
except ImportError:
    # Fallback for older Kodi versions
    translatePath = xbmc.translatePath

from imdb import getOriginalAspectRatio

# TODO: Improve IMDb/TVDB ID detection to be more robust across different providers
# - Handle cases where uniqueid.imdb/tvdb may not be available
# - Support more providers (Plex, Emby, local files, etc.)
# - Consider using TVDB ID to find IMDb number for episodes
# - Add fallback strategies for different metadata sources

ZOOM_RATE_LIMIT_MS = 500


def notify(msg):
    xbmcgui.Dialog().notification("Remove Black Bars (GBM)", msg, None, 1000)


def translate_profile_path(*paths):
    try:
        profile = translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
    except Exception:
        profile = xbmcaddon.Addon().getAddonInfo("profile")
        if profile.startswith("special://"):
            profile = translatePath(profile)
    return os.path.join(profile, *paths)


def get_writable_cache_path(filename="cache.json"):
    """
    Get a writable cache path using the addon profile directory.
    Returns None if the profile directory is not writable (cache disabled).
    """
    try:
        profile_path = translate_profile_path(filename)
        directory = os.path.dirname(profile_path)
        if directory:
            try:
                os.makedirs(directory, exist_ok=True)
                xbmc.log(f"service.remove.black.bars.gbm: Attempting to use profile cache directory: {profile_path}", level=xbmc.LOGDEBUG)
            except (OSError, IOError) as e:
                xbmc.log(f"service.remove.black.bars.gbm: Failed to create profile cache directory: {e}", level=xbmc.LOGDEBUG)
                return None
            if os.path.exists(directory) and os.access(directory, os.W_OK):
                # Test write access
                try:
                    test_file = os.path.join(directory, ".test_write")
                    with open(test_file, "w") as f:
                        f.write("test")
                    os.remove(test_file)
                    xbmc.log(f"service.remove.black.bars.gbm: Profile cache directory is writable: {profile_path}", level=xbmc.LOGDEBUG)
                    return profile_path
                except Exception as e:
                    xbmc.log(f"service.remove.black.bars.gbm: Profile cache directory not writable: {e}", level=xbmc.LOGDEBUG)
                    return None
    except Exception as e:
        xbmc.log(f"service.remove.black.bars.gbm: Profile directory not available: {e}", level=xbmc.LOGDEBUG)
    
    # If profile directory is not writable, return None (cache disabled)
    xbmc.log("service.remove.black.bars.gbm: Profile cache directory not available, cache disabled", level=xbmc.LOGWARNING)
    return None


class KodiMetadataProvider:
    def get_aspect_ratio(self, video_info_tag):
        """
        Get aspect ratio from Kodi metadata using VideoPlayer.VideoAspect InfoLabel.
        Returns aspect ratio as integer (e.g., 178 for 16:9, 240 for 2.40:1).
        See ASPECT_RATIO_DETECTION.md for alternative methods (JSON-RPC).
        """
        try:
            label = xbmc.getInfoLabel("VideoPlayer.VideoAspect")
            xbmc.log(f"service.remove.black.bars.gbm: VideoPlayer.VideoAspect returned: '{label}'", level=xbmc.LOGDEBUG)
            if label and label != "VideoPlayer.VideoAspect":
                # Format might be "2.35AR" or "2.35" or "2.35:1"
                cleaned = label.replace("AR", "").split(":")[0].strip()
                try:
                    ratio = int((float(cleaned) + 0.005) * 100)
                    xbmc.log(f"service.remove.black.bars.gbm: Kodi metadata: {ratio}", level=xbmc.LOGINFO)
                    return ratio
                except ValueError as e:
                    xbmc.log(f"service.remove.black.bars.gbm: Failed to parse VideoPlayer.VideoAspect '{label}': {e}", level=xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: VideoPlayer.VideoAspect error: {e}", level=xbmc.LOGDEBUG)
        
        return None


class JsonCacheProvider:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.path = get_writable_cache_path("cache.json")
        self._cache = {}
        if self.enabled and self.path:
            self._ensure_dir()
            self._cache = self._load()
        elif self.enabled and not self.path:
            xbmc.log("service.remove.black.bars.gbm: No writable cache path available, cache disabled", level=xbmc.LOGWARNING)
            self.enabled = False

    def _ensure_dir(self):
        if not self.path:
            return
        try:
            directory = os.path.dirname(self.path)
            if directory and not os.path.isdir(directory):
                os.makedirs(directory, exist_ok=True)
                xbmc.log(f"service.remove.black.bars.gbm: Created cache directory: {directory}", level=xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: Failed to ensure cache dir: {e}", level=xbmc.LOGWARNING)

    def _load(self):
        if not self.enabled or not self.path:
            return {}
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                    xbmc.log(f"service.remove.black.bars.gbm: Loaded cache with {len(cache)} entries from {self.path}", level=xbmc.LOGDEBUG)
                    xbmc.log(f"service.remove.black.bars.gbm: Cache location: {self.path}", level=xbmc.LOGINFO)
                    return cache
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: Failed to load cache: {e}", level=xbmc.LOGWARNING)
        return {}

    def _save(self):
        if not self.enabled or not self.path:
            return
        try:
            xbmc.log(f"service.remove.black.bars.gbm: Attempting to save cache with {len(self._cache)} entries to {self.path}", level=xbmc.LOGDEBUG)
            self._ensure_dir()
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f)
                xbmc.log(f"service.remove.black.bars.gbm: Saved cache with {len(self._cache)} entries to {self.path}", level=xbmc.LOGDEBUG)
                xbmc.log(f"service.remove.black.bars.gbm: Cache location: {self.path}", level=xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: Failed to save cache to {self.path}: {e}", level=xbmc.LOGWARNING)
    
    def clear(self):
        """Clear the cache"""
        try:
            self._cache = {}
            if self.path and os.path.exists(self.path):
                os.remove(self.path)
                xbmc.log(f"service.remove.black.bars.gbm: Cache cleared from {self.path}", level=xbmc.LOGINFO)
                return True
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: Failed to clear cache: {e}", level=xbmc.LOGWARNING)
        return False

    def _make_key(self, title, year=None, imdb_id=None):
        if imdb_id:
            return "imdb:" + str(imdb_id)
        key = (title or "").strip().lower()
        if year:
            key += f" ({year})"
        return key

    def get(self, title, year=None, imdb_id=None):
        try:
            key = self._make_key(title, year, imdb_id)
            value = self._cache.get(key)
            return int(value) if value is not None else None
        except Exception:
            return None

    def store(self, title, year, ratio, imdb_id=None):
        try:
            key = self._make_key(title, year, imdb_id)
            self._cache[key] = int(ratio)
            self._save()
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: Failed to store cache: " + str(e), level=xbmc.LOGWARNING)


class IMDbProvider:
    def get_aspect_ratio(self, title, imdb_number=None):
        try:
            value = getOriginalAspectRatio(title, imdb_number=imdb_number)
            if isinstance(value, list):
                value = value[0] if value else None
            if value:
                return int(value)
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: IMDbProvider error: " + str(e), level=xbmc.LOGWARNING)
        return None


class ZoomApplier:
    def __init__(self):
        self.last_zoom_time_ms = 0
        self.last_applied_ratio = None

    def _is_video_playing_fullscreen(self, player):
        try:
            if not player.isPlayingVideo():
                xbmc.log("service.remove.black.bars.gbm: Not playing video", level=xbmc.LOGDEBUG)
                return False
            window_id = xbmcgui.getCurrentWindowId()
            xbmc.log(f"service.remove.black.bars.gbm: Current window ID: {window_id}", level=xbmc.LOGDEBUG)
            if window_id != 12005:
                xbmc.log(f"service.remove.black.bars.gbm: Not in fullscreen window (expected 12005, got {window_id})", level=xbmc.LOGDEBUG)
                return False
            if not player.isPlaying():
                xbmc.log("service.remove.black.bars.gbm: Player not playing", level=xbmc.LOGDEBUG)
                return False
            return True
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: _is_video_playing_fullscreen error: {e}", level=xbmc.LOGDEBUG)
            return False

    def _calculate_zoom(self, detected_ratio, zoom_narrow_ratios=False):
        if detected_ratio > 177:
            return detected_ratio / 177.0
        elif zoom_narrow_ratios and detected_ratio < 177:
            return 177.0 / detected_ratio
        return 1.0

    def apply_zoom(self, detected_ratio, player, zoom_narrow_ratios=False):
        try:
            # Skip if same ratio already applied
            if self.last_applied_ratio == detected_ratio:
                xbmc.log(f"service.remove.black.bars.gbm: Zoom already applied for ratio {detected_ratio}, skipping", level=xbmc.LOGDEBUG)
                return False
            
            now_ms = int(time.time() * 1000)
            if now_ms - self.last_zoom_time_ms < ZOOM_RATE_LIMIT_MS:
                xbmc.log("service.remove.black.bars.gbm: Zoom rate limited", level=xbmc.LOGDEBUG)
                return False
            if not self._is_video_playing_fullscreen(player):
                xbmc.log("service.remove.black.bars.gbm: Video not playing fullscreen", level=xbmc.LOGDEBUG)
                return False
            zoom_amount = self._calculate_zoom(detected_ratio, zoom_narrow_ratios)
            xbmc.log(f"service.remove.black.bars.gbm: Applying zoom {zoom_amount} for ratio {detected_ratio}", level=xbmc.LOGINFO)
            json_cmd = json.dumps({
                "jsonrpc": "2.0",
                "method": "Player.SetViewMode",
                "params": {
                    "viewmode": {
                        "zoom": zoom_amount
                    }
                },
                "id": 1
            })
            result = xbmc.executeJSONRPC(json_cmd)
            if result:
                try:
                    result_json = json.loads(result)
                    if "error" in result_json:
                        xbmc.log(f"service.remove.black.bars.gbm: JSON-RPC error: {result_json.get('error', {})}", level=xbmc.LOGWARNING)
                except Exception:
                    pass
            self.last_zoom_time_ms = now_ms
            self.last_applied_ratio = detected_ratio
            if zoom_amount > 1.0:
                notify("Zoom applied {:.2f}".format(zoom_amount))
            return True
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: Zoom error: " + str(e), level=xbmc.LOGERROR)
            return False


class Service(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.monitor = xbmc.Monitor()
        self.zoom = ZoomApplier()
        self.kodi = KodiMetadataProvider()
        self._addon = xbmcaddon.Addon()
        cache_enabled = self._get_cache_enabled()
        self.cache = JsonCacheProvider(enabled=cache_enabled)
        self.imdb = IMDbProvider()

        if "toggle" in sys.argv:
            if xbmcgui.Window(10000).getProperty("removeblackbars_status") == "on":
                self.show_original()
            else:
                self.on_av_started()

    def _read_settings(self):
        try:
            imdb_enabled = self._addon.getSetting("enable_imdb") == "true"
        except Exception:
            imdb_enabled = False
        return imdb_enabled

    def _get_cache_enabled(self):
        try:
            return self._addon.getSetting("enable_cache") == "true"
        except Exception:
            return True

    def _extract_title_year(self, video_info_tag):
        title = None
        year = None
        try:
            media_type = video_info_tag.getMediaType()
            if media_type == "episode":
                title = video_info_tag.getTVShowTitle()
                year = video_info_tag.getYear()
            else:
                title = video_info_tag.getTitle() or video_info_tag.getOriginalTitle()
                year = video_info_tag.getYear()
                if not title:
                    filename = video_info_tag.getFilenameAndPath()
                    if filename:
                        title = os.path.basename(filename).rsplit(".", 1)[0]
        except Exception:
            pass
        return title, year

    def _detect_aspect_ratio(self):
        try:
            if not self.isPlayingVideo():
                xbmc.log("service.remove.black.bars.gbm: Not playing video, skipping detection", level=xbmc.LOGDEBUG)
                return None
            video_info_tag = self.getVideoInfoTag()
            if not video_info_tag:
                xbmc.log("service.remove.black.bars.gbm: No video info tag available", level=xbmc.LOGDEBUG)
                return None

            title, year = self._extract_title_year(video_info_tag)
            
            # Get IMDb number from JSON-RPC
            imdb_number = None
            try:
                json_cmd = json.dumps({
                    "jsonrpc": "2.0",
                    "method": "Player.GetItem",
                    "params": {
                        "playerid": 1,
                        "properties": ["uniqueid"]
                    },
                    "id": 1
                })
                result = xbmc.executeJSONRPC(json_cmd)
                if result:
                    result_json = json.loads(result)
                    if "result" in result_json and "item" in result_json["result"]:
                        item = result_json["result"]["item"]
                        item_type = item.get("type")
                        if item_type in ("movie", "episode") and "uniqueid" in item and "imdb" in item["uniqueid"]:
                            imdb_number = item["uniqueid"]["imdb"]
            except Exception:
                pass
            
            xbmc.log(f"service.remove.black.bars.gbm: Detecting aspect ratio - title='{title}', year={year}, imdb={imdb_number}", level=xbmc.LOGDEBUG)

            # 1) IMDb (first priority, cache only IMDb results)
            imdb_enabled, _ = self._read_settings()
            if imdb_enabled:
                # Try cache first
                ratio = self.cache.get(title, year, imdb_id=imdb_number if imdb_number else None)
                if ratio:
                    xbmc.log(f"service.remove.black.bars.gbm: Using IMDb cache: {ratio}", level=xbmc.LOGINFO)
                    return ratio
                
                # Try IMDb provider
                xbmc.log("service.remove.black.bars.gbm: IMDb cache miss, fetching from IMDb", level=xbmc.LOGDEBUG)
                ratio = self.imdb.get_aspect_ratio(title, imdb_number=imdb_number if imdb_number else None)
                if ratio:
                    xbmc.log(f"service.remove.black.bars.gbm: Using IMDb: {ratio}", level=xbmc.LOGINFO)
                    self.cache.store(title, year, ratio, imdb_id=imdb_number if imdb_number else None)
                    return ratio

            # 2) Kodi metadata (fallback if IMDb unavailable or not found)
            xbmc.log("service.remove.black.bars.gbm: Trying Kodi metadata", level=xbmc.LOGDEBUG)
            ratio = self.kodi.get_aspect_ratio(video_info_tag)
            if ratio:
                xbmc.log(f"service.remove.black.bars.gbm: Using Kodi metadata: {ratio}", level=xbmc.LOGINFO)
                return ratio

            xbmc.log("service.remove.black.bars.gbm: No aspect ratio found from any provider", level=xbmc.LOGDEBUG)
            return None
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: detect ratio error: " + str(e), level=xbmc.LOGERROR)
            return None

    def onAVStarted(self):
        self.on_av_started()

    def onAVChange(self):
        # Disabled to avoid loop: changing zoom triggers onAVChange which re-applies zoom
        pass

    def on_av_started(self):
        try:
            xbmc.log("service.remove.black.bars.gbm: on_av_started called", level=xbmc.LOGINFO)
            self.zoom.last_applied_ratio = None
            xbmcgui.Window(10000).setProperty("removeblackbars_status", "on")
            ratio = self._detect_aspect_ratio()
            xbmc.log(f"service.remove.black.bars.gbm: Detected aspect ratio: {ratio}", level=xbmc.LOGINFO)
            if ratio:
                _, zoom_narrow_ratios = self._read_settings()
                self.zoom.apply_zoom(ratio, self, zoom_narrow_ratios)
            else:
                xbmc.log("service.remove.black.bars.gbm: No aspect ratio detected, skipping zoom", level=xbmc.LOGINFO)
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: on_av_started error: " + str(e), level=xbmc.LOGERROR)


    def onPlayBackStopped(self):
        try:
            xbmcgui.Window(10000).setProperty("removeblackbars_status", "off")
            self.zoom.last_applied_ratio = None
        except Exception:
            pass

    def onPlayBackEnded(self):
        try:
            xbmcgui.Window(10000).setProperty("removeblackbars_status", "off")
            self.zoom.last_applied_ratio = None
        except Exception:
            pass

    def show_original(self):
        try:
            xbmcgui.Window(10000).setProperty("removeblackbars_status", "off")
            json_cmd = json.dumps({
                "jsonrpc": "2.0",
                "method": "Player.SetViewMode",
                "params": {
                    "viewmode": {
                        "zoom": 1.0
                    }
                },
                "id": 1
            })
            xbmc.executeJSONRPC(json_cmd)
            notify("Original view")
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: show_original error: " + str(e), level=xbmc.LOGERROR)


def clear_cache():
    """Clear the IMDb cache - called from settings action"""
    try:
        xbmc.log("service.remove.black.bars.gbm: clear_cache() called", level=xbmc.LOGINFO)
        addon = xbmcaddon.Addon()
        cache_enabled = addon.getSetting("enable_cache") == "true"
        if not cache_enabled:
            xbmcgui.Dialog().ok("IMDb Cache", "IMDb cache is disabled. Enable it first in settings.")
            return
        
        cache = JsonCacheProvider(enabled=True)
        cache_entries = len(cache._cache) if cache._cache else 0
        xbmc.log(f"service.remove.black.bars.gbm: Cache has {cache_entries} entries before clearing", level=xbmc.LOGINFO)
        
        if cache.clear():
            notify("IMDb cache cleared successfully")
            if cache_entries > 0:
                msg = f"IMDb cache cleared successfully.\n{cache_entries} entries removed."
            else:
                msg = "IMDb cache cleared successfully."
            xbmc.log(f"service.remove.black.bars.gbm: Showing dialog: {msg}", level=xbmc.LOGINFO)
            xbmcgui.Dialog().ok("IMDb Cache", msg)
        else:
            xbmc.log("service.remove.black.bars.gbm: Cache clear returned False", level=xbmc.LOGINFO)
            xbmcgui.Dialog().ok("IMDb Cache", "IMDb cache is already empty or could not be cleared.")
    except Exception as e:
        xbmc.log("service.remove.black.bars.gbm: Error clearing IMDb cache: " + str(e), level=xbmc.LOGERROR)
        import traceback
        xbmc.log("service.remove.black.bars.gbm: Traceback: " + traceback.format_exc(), level=xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", f"Failed to clear IMDb cache: {e}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "clear_cache":
        clear_cache()
        return
    
    xbmc.log("service.remove.black.bars.gbm: Service starting", level=xbmc.LOGINFO)
    service = Service()
    xbmc.log("service.remove.black.bars.gbm: Service initialized", level=xbmc.LOGINFO)
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break
    xbmc.log("service.remove.black.bars.gbm: Service stopping", level=xbmc.LOGINFO)


if __name__ == "__main__":
    main()
