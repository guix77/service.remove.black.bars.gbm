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

# Note: IMDb number is obtained via JSON-RPC Player.GetItem with uniqueid property.
# This is the standard method as there's no direct InfoLabel equivalent to VideoPlayer.VideoAspect.

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
            except (OSError, IOError) as e:
                xbmc.log(f"service.remove.black.bars.gbm: Failed to create cache directory: {e}", level=xbmc.LOGDEBUG)
                return None
            if os.path.exists(directory) and os.access(directory, os.W_OK):
                # Test write access
                try:
                    test_file = os.path.join(directory, ".test_write")
                    with open(test_file, "w") as f:
                        f.write("test")
                    os.remove(test_file)
                    xbmc.log(f"service.remove.black.bars.gbm: Cache directory ready: {profile_path}", level=xbmc.LOGDEBUG)
                    return profile_path
                except Exception as e:
                    xbmc.log(f"service.remove.black.bars.gbm: Cache directory not writable: {e}", level=xbmc.LOGDEBUG)
                    return None
    except Exception as e:
        xbmc.log(f"service.remove.black.bars.gbm: Cache directory error: {e}", level=xbmc.LOGDEBUG)

    # If profile directory is not writable, return None (cache disabled)
    xbmc.log("service.remove.black.bars.gbm: Profile cache directory not available, cache disabled", level=xbmc.LOGWARNING)
    return None


class KodiMetadataProvider:
    def get_aspect_ratio(self, video_info_tag, reason=None):
        """
        Get aspect ratio from Kodi metadata using VideoPlayer.VideoAspect InfoLabel.
        Returns aspect ratio as integer (e.g., 178 for 16:9, 240 for 2.40:1).
        
        Args:
            video_info_tag: Video info tag (unused but kept for compatibility)
            reason: Optional reason string to include in log message
        """
        try:
            reason_text = f" ({reason})" if reason else ""
            label = xbmc.getInfoLabel("VideoPlayer.VideoAspect")
            xbmc.log(f"service.remove.black.bars.gbm: VideoPlayer.VideoAspect{reason_text}: '{label}'", level=xbmc.LOGDEBUG)
            if label and label != "VideoPlayer.VideoAspect":
                # Format might be "2.35AR" or "2.35" or "2.35:1"
                cleaned = label.replace("AR", "").split(":")[0].strip()
                try:
                    ratio = int((float(cleaned) + 0.005) * 100)
                    xbmc.log(f"service.remove.black.bars.gbm: Parsed VideoAspect: {ratio} from '{label}'", level=xbmc.LOGDEBUG)
                    return ratio
                except ValueError as e:
                    xbmc.log(f"service.remove.black.bars.gbm: Failed to parse VideoAspect '{label}': {e}", level=xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: VideoAspect error: {e}", level=xbmc.LOGDEBUG)
        
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
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: Failed to ensure cache dir: {e}", level=xbmc.LOGWARNING)

    def _load(self):
        if not self.enabled or not self.path:
            return {}
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                    xbmc.log(f"service.remove.black.bars.gbm: Cache loaded: {len(cache)} entries from {self.path}", level=xbmc.LOGDEBUG)
                    xbmc.log(f"service.remove.black.bars.gbm: Cache location: {self.path}", level=xbmc.LOGINFO)
                    return cache
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: Failed to load cache: {e}", level=xbmc.LOGWARNING)
        return {}

    def _save(self):
        if not self.enabled or not self.path:
            return
        try:
            self._ensure_dir()
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f)
                xbmc.log(f"service.remove.black.bars.gbm: Cache saved: {len(self._cache)} entries", level=xbmc.LOGDEBUG)
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
                xbmc.log("service.remove.black.bars.gbm: Zoom skipped: not playing video", level=xbmc.LOGDEBUG)
                return False
            window_id = xbmcgui.getCurrentWindowId()
            if window_id != 12005:
                xbmc.log(f"service.remove.black.bars.gbm: Zoom skipped: not fullscreen (window {window_id}, expected 12005)", level=xbmc.LOGDEBUG)
                return False
            if not player.isPlaying():
                xbmc.log("service.remove.black.bars.gbm: Zoom skipped: player paused/stopped", level=xbmc.LOGDEBUG)
                return False
            return True
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: Fullscreen check error: {e}", level=xbmc.LOGDEBUG)
            return False

    def _calculate_zoom(self, detected_ratio, zoom_narrow_ratios=False, file_ratio=None):
        """
        Calculate zoom amount based on detected ratio.
        
        Args:
            detected_ratio: The detected content aspect ratio (e.g., from IMDb)
            zoom_narrow_ratios: Whether to zoom narrow ratios (< 16:9)
            file_ratio: Optional file aspect ratio (may include encoded black bars)
                       If provided and different from detected_ratio, use it for zoom calculation
        """
        # If file_ratio is provided and different from detected_ratio, we have encoded black bars
        # Zoom should be calculated from file_ratio to detected_ratio
        if file_ratio and file_ratio != detected_ratio:
            return file_ratio / float(detected_ratio)
        
        # If file_ratio is available and close to 16:9 (177), no need to zoom
        # even if detected_ratio > 177 (file is already 16:9, content fits without black bars)
        if file_ratio and 175 <= file_ratio <= 180:
            return 1.0
        
        # Normal zoom calculation
        if detected_ratio > 177:
            return detected_ratio / 177.0
        elif zoom_narrow_ratios and detected_ratio < 177:
            return 177.0 / detected_ratio
        return 1.0

    def apply_zoom(self, detected_ratio, player, zoom_narrow_ratios=False, file_ratio=None, title=None):
        try:
            if self.last_applied_ratio == detected_ratio:
                xbmc.log(f"service.remove.black.bars.gbm: Zoom skipped: already applied for ratio {detected_ratio}", level=xbmc.LOGDEBUG)
                return False
            
            now_ms = int(time.time() * 1000)
            if now_ms - self.last_zoom_time_ms < ZOOM_RATE_LIMIT_MS:
                xbmc.log(f"service.remove.black.bars.gbm: Zoom skipped: rate limited ({now_ms - self.last_zoom_time_ms}ms < {ZOOM_RATE_LIMIT_MS}ms)", level=xbmc.LOGDEBUG)
                return False
            if not self._is_video_playing_fullscreen(player):
                return False
            zoom_amount = self._calculate_zoom(detected_ratio, zoom_narrow_ratios, file_ratio)
            title_display = title or "video"
            xbmc.log(f"service.remove.black.bars.gbm: Applying zoom {zoom_amount:.2f} on {title_display} to remove black bars", level=xbmc.LOGINFO)
            if file_ratio and file_ratio != detected_ratio:
                xbmc.log(f"service.remove.black.bars.gbm: Zoom calculation: file={file_ratio}, content={detected_ratio}, zoom={zoom_amount:.3f}", level=xbmc.LOGDEBUG)
            else:
                xbmc.log(f"service.remove.black.bars.gbm: Zoom calculation: ratio={detected_ratio}, zoom={zoom_amount:.3f}", level=xbmc.LOGDEBUG)
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
        """Read addon settings."""
        try:
            imdb_enabled = self._addon.getSetting("enable_imdb") == "true"
        except Exception:
            imdb_enabled = False
        try:
            zoom_narrow_ratios = self._addon.getSetting("zoom_narrow_ratios") == "true"
        except Exception:
            zoom_narrow_ratios = False
        return imdb_enabled, zoom_narrow_ratios

    def _get_cache_enabled(self):
        """Check if cache is enabled in settings."""
        try:
            return self._addon.getSetting("enable_cache") == "true"
        except Exception:
            return True

    def _extract_title_year(self, video_info_tag):
        """Extract title and year from video info tag."""
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
                xbmc.log("service.remove.black.bars.gbm: Detection skipped: not playing video", level=xbmc.LOGDEBUG)
                return None
            video_info_tag = self.getVideoInfoTag()
            if not video_info_tag:
                xbmc.log("service.remove.black.bars.gbm: Detection skipped: no video info tag", level=xbmc.LOGDEBUG)
                return None

            title, year = self._extract_title_year(video_info_tag)

            # Get IMDb number from JSON-RPC (more reliable than title search)
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
            
            # Format title for logging
            title_display = title or "Unknown"
            if year:
                title_display = f"{title_display} ({year})"
            
            xbmc.log(f"service.remove.black.bars.gbm: Detecting black bars for {title_display}", level=xbmc.LOGINFO)
            xbmc.log(f"service.remove.black.bars.gbm: Detection params: title='{title}', year={year}, imdb={imdb_number}", level=xbmc.LOGDEBUG)

            # 1) IMDb (first priority, cache only IMDb results)
            imdb_enabled, _ = self._read_settings()
            imdb_ratio = None
            file_ratio = None
            encoded_black_bars_detected = False
            
            if imdb_enabled:
                # Try cache first (use IMDb number if available for more precise cache key)
                imdb_ratio = self.cache.get(title, year, imdb_id=imdb_number)
                if imdb_ratio:
                    xbmc.log(f"service.remove.black.bars.gbm: IMDb cache hit: ratio={imdb_ratio}", level=xbmc.LOGDEBUG)
                else:
                    # Try IMDb provider (use IMDb number if available for direct access)
                    xbmc.log("service.remove.black.bars.gbm: IMDb cache miss, querying IMDb API", level=xbmc.LOGDEBUG)
                    imdb_ratio = self.imdb.get_aspect_ratio(title, imdb_number=imdb_number)
                    if imdb_ratio:
                        xbmc.log(f"service.remove.black.bars.gbm: IMDb API result: ratio={imdb_ratio}", level=xbmc.LOGDEBUG)
                        self.cache.store(title, year, imdb_ratio, imdb_id=imdb_number)
                    else:
                        xbmc.log("service.remove.black.bars.gbm: IMDb API: no ratio found", level=xbmc.LOGDEBUG)
                
                # If we have IMDb ratio, get file ratio for encoded black bars detection
                if imdb_ratio:
                    file_ratio_temp = self.kodi.get_aspect_ratio(video_info_tag, reason="for encoded black bars detection")
                    # Compare IMDb ratio (content) with file ratio (may have encoded black bars)
                    if file_ratio_temp:
                        difference = abs(file_ratio_temp - imdb_ratio)
                        threshold = max(5, int(imdb_ratio * 0.05))  # 5% of IMDb ratio, minimum 5
                        if difference > threshold:
                            encoded_black_bars_detected = True
                            file_ratio = file_ratio_temp
                            xbmc.log(f"service.remove.black.bars.gbm: Encoded black bars detected: IMDb={imdb_ratio}, file={file_ratio}, diff={difference} (threshold={threshold})", level=xbmc.LOGDEBUG)
                        else:
                            # Store file_ratio even if no encoded black bars (for zoom calculation)
                            file_ratio = file_ratio_temp
                            xbmc.log(f"service.remove.black.bars.gbm: No encoded black bars: IMDb={imdb_ratio}, file={file_ratio}, diff={difference} (threshold={threshold})", level=xbmc.LOGDEBUG)

            # 2) Kodi metadata (fallback if IMDb unavailable or not found)
            if not imdb_ratio:
                xbmc.log("service.remove.black.bars.gbm: IMDb unavailable, using Kodi metadata fallback", level=xbmc.LOGDEBUG)
                file_ratio = self.kodi.get_aspect_ratio(video_info_tag, reason="for ratio detection")
                if file_ratio:
                    xbmc.log(f"service.remove.black.bars.gbm: Kodi metadata: ratio={file_ratio}", level=xbmc.LOGDEBUG)

            # Return tuple (detected_ratio, file_ratio, title_display)
            # detected_ratio is IMDb ratio if available, otherwise file_ratio
            # file_ratio is set if available (for zoom calculation, even if no encoded black bars)
            detected_ratio = imdb_ratio if imdb_ratio else file_ratio
            if detected_ratio:
                source = "IMDb" if imdb_ratio else "Kodi metadata"
                xbmc.log(f"service.remove.black.bars.gbm: Detection complete: ratio={detected_ratio} from {source}", level=xbmc.LOGDEBUG)
                return (detected_ratio, file_ratio, title_display)

            xbmc.log("service.remove.black.bars.gbm: Detection failed: no aspect ratio found", level=xbmc.LOGDEBUG)
            return None
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: detect ratio error: " + str(e), level=xbmc.LOGERROR)
            return None

    def onAVStarted(self):
        self.on_av_started()

    def onAVChange(self):
        """Disabled to avoid loop: changing zoom triggers onAVChange which re-applies zoom."""
        pass

    def on_av_started(self):
        try:
            self.zoom.last_applied_ratio = None
            xbmcgui.Window(10000).setProperty("removeblackbars_status", "on")
            result = self._detect_aspect_ratio()
            if result:
                detected_ratio, file_ratio, title_display = result
                _, zoom_narrow_ratios = self._read_settings()
                self.zoom.apply_zoom(detected_ratio, self, zoom_narrow_ratios, file_ratio, title_display)
            else:
                xbmc.log("service.remove.black.bars.gbm: Zoom skipped: no aspect ratio detected", level=xbmc.LOGDEBUG)
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
