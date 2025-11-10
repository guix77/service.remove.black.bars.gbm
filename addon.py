import os
import sys
import json
import time

import xbmc
import xbmcaddon
import xbmcgui

from imdb import getOriginalAspectRatio

ZOOM_RATE_LIMIT_MS = 500


def notify(msg):
    xbmcgui.Dialog().notification("Remove Black Bars (GBM)", msg, None, 1000)


def translate_profile_path(*paths):
    try:
        profile = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
    except Exception:
        profile = xbmcaddon.Addon().getAddonInfo("profile")
    return os.path.join(profile, *paths)


def is_local_file(path):
    if not path:
        return False
    if path.startswith(("http://", "https://", "smb://", "nfs://", "ftp://")):
        return False
    if path.startswith("/") or (os.name == "nt" and ":" in path):
        try:
            return os.path.exists(path)
        except Exception:
            return False
    return False


class KodiMetadataProvider:
    def get_aspect_ratio(self, video_info_tag):
        # Force test all methods to see which ones work
        # VideoPlayer.VideoAspect gives the aspect ratio of the video file as it is
        # (may include hardcoded black bars for Jellyfin/streaming sources)
        
        results = {}  # Store results from all methods
        
        # Try method 1: VideoPlayer.VideoAspect (documented in Emby forum)
        try:
            xbmc.log("service.remove.black.bars.gbm: [TEST] Trying VideoPlayer.VideoAspect info label", level=xbmc.LOGDEBUG)
            label = xbmc.getInfoLabel("VideoPlayer.VideoAspect")
            xbmc.log(f"service.remove.black.bars.gbm: [TEST] VideoPlayer.VideoAspect returned: '{label}'", level=xbmc.LOGDEBUG)
            if label and label != "VideoPlayer.VideoAspect":
                # Format might be "2.35AR" or "2.35" or "2.35:1"
                # Remove "AR" suffix if present
                cleaned = label.replace("AR", "").split(":")[0].strip()
                xbmc.log(f"service.remove.black.bars.gbm: [TEST] Cleaned aspect ratio string: '{cleaned}'", level=xbmc.LOGDEBUG)
                try:
                    ratio = int((float(cleaned) + 0.005) * 100)
                    xbmc.log(f"service.remove.black.bars.gbm: [TEST] VideoPlayer.VideoAspect SUCCESS: {ratio}", level=xbmc.LOGINFO)
                    results["VideoPlayer.VideoAspect"] = ratio
                except ValueError as e:
                    xbmc.log(f"service.remove.black.bars.gbm: [TEST] VideoPlayer.VideoAspect FAILED (parse error): {e}", level=xbmc.LOGWARNING)
                    results["VideoPlayer.VideoAspect"] = None
            else:
                xbmc.log("service.remove.black.bars.gbm: [TEST] VideoPlayer.VideoAspect FAILED (not available)", level=xbmc.LOGDEBUG)
                results["VideoPlayer.VideoAspect"] = None
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: [TEST] VideoPlayer.VideoAspect FAILED (exception): {e}", level=xbmc.LOGDEBUG)
            results["VideoPlayer.VideoAspect"] = None
        
        # Try method 2: ListItem.VideoAspect (documented in Emby forum)
        try:
            xbmc.log("service.remove.black.bars.gbm: [TEST] Trying ListItem.VideoAspect info label", level=xbmc.LOGDEBUG)
            label = xbmc.getInfoLabel("ListItem.VideoAspect")
            xbmc.log(f"service.remove.black.bars.gbm: [TEST] ListItem.VideoAspect returned: '{label}'", level=xbmc.LOGDEBUG)
            if label and label != "ListItem.VideoAspect":
                # Format might be "2.35AR" or "2.35" or "2.35:1"
                # Remove "AR" suffix if present
                cleaned = label.replace("AR", "").split(":")[0].strip()
                xbmc.log(f"service.remove.black.bars.gbm: [TEST] Cleaned aspect ratio string: '{cleaned}'", level=xbmc.LOGDEBUG)
                try:
                    ratio = int((float(cleaned) + 0.005) * 100)
                    xbmc.log(f"service.remove.black.bars.gbm: [TEST] ListItem.VideoAspect SUCCESS: {ratio}", level=xbmc.LOGINFO)
                    results["ListItem.VideoAspect"] = ratio
                except ValueError as e:
                    xbmc.log(f"service.remove.black.bars.gbm: [TEST] ListItem.VideoAspect FAILED (parse error): {e}", level=xbmc.LOGWARNING)
                    results["ListItem.VideoAspect"] = None
            else:
                xbmc.log("service.remove.black.bars.gbm: [TEST] ListItem.VideoAspect FAILED (not available)", level=xbmc.LOGDEBUG)
                results["ListItem.VideoAspect"] = None
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: [TEST] ListItem.VideoAspect FAILED (exception): {e}", level=xbmc.LOGDEBUG)
            results["ListItem.VideoAspect"] = None
        
        # Try method 3: VideoPlayer.AspectRatio (fallback, may not work)
        try:
            xbmc.log("service.remove.black.bars.gbm: [TEST] Trying VideoPlayer.AspectRatio info label", level=xbmc.LOGDEBUG)
            label = xbmc.getInfoLabel("VideoPlayer.AspectRatio")
            xbmc.log(f"service.remove.black.bars.gbm: [TEST] VideoPlayer.AspectRatio returned: '{label}'", level=xbmc.LOGDEBUG)
            # If getInfoLabel returns the label name itself, it means the label is not available
            if not label or label == "VideoPlayer.AspectRatio":
                xbmc.log("service.remove.black.bars.gbm: [TEST] VideoPlayer.AspectRatio FAILED (not available)", level=xbmc.LOGDEBUG)
                results["VideoPlayer.AspectRatio"] = None
            else:
                # Common formats: "1.78" or "1.78:1"
                cleaned = label.split(":")[0].strip()
                xbmc.log(f"service.remove.black.bars.gbm: [TEST] Cleaned aspect ratio string: '{cleaned}'", level=xbmc.LOGDEBUG)
                try:
                    ratio = int((float(cleaned) + 0.005) * 100)
                    xbmc.log(f"service.remove.black.bars.gbm: [TEST] VideoPlayer.AspectRatio SUCCESS: {ratio}", level=xbmc.LOGINFO)
                    results["VideoPlayer.AspectRatio"] = ratio
                except ValueError as e:
                    xbmc.log(f"service.remove.black.bars.gbm: [TEST] VideoPlayer.AspectRatio FAILED (parse error): {e}", level=xbmc.LOGWARNING)
                    results["VideoPlayer.AspectRatio"] = None
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: [TEST] VideoPlayer.AspectRatio FAILED (exception): {e}", level=xbmc.LOGDEBUG)
            results["VideoPlayer.AspectRatio"] = None
        
        # Try method 4: JSON-RPC Player.GetProperties (may work for Jellyfin/streaming)
        try:
            xbmc.log("service.remove.black.bars.gbm: [TEST] Trying JSON-RPC Player.GetProperties", level=xbmc.LOGDEBUG)
            json_cmd = json.dumps({
                "jsonrpc": "2.0",
                "method": "Player.GetProperties",
                "params": {
                    "playerid": 1,
                    "properties": ["streamdetails"]
                },
                "id": 1
            })
            result = xbmc.executeJSONRPC(json_cmd)
            xbmc.log(f"service.remove.black.bars.gbm: [TEST] JSON-RPC result: {result[:200] if result else 'None'}", level=xbmc.LOGDEBUG)
            if result:
                try:
                    result_json = json.loads(result)
                    if "result" in result_json and "streamdetails" in result_json["result"]:
                        streamdetails = result_json["result"]["streamdetails"]
                        if "video" in streamdetails and len(streamdetails["video"]) > 0:
                            video_stream = streamdetails["video"][0]
                            if "aspect" in video_stream:
                                aspect = video_stream["aspect"]
                                xbmc.log(f"service.remove.black.bars.gbm: [TEST] Found aspect ratio from JSON-RPC: {aspect}", level=xbmc.LOGDEBUG)
                                # Convert to integer format (e.g., 1.78 -> 178)
                                ratio = int((float(aspect) + 0.005) * 100)
                                xbmc.log(f"service.remove.black.bars.gbm: [TEST] JSON-RPC SUCCESS: {ratio}", level=xbmc.LOGINFO)
                                results["JSON-RPC"] = ratio
                            else:
                                xbmc.log("service.remove.black.bars.gbm: [TEST] JSON-RPC FAILED (no 'aspect' in video stream)", level=xbmc.LOGDEBUG)
                                results["JSON-RPC"] = None
                        else:
                            xbmc.log("service.remove.black.bars.gbm: [TEST] JSON-RPC FAILED (no video stream)", level=xbmc.LOGDEBUG)
                            results["JSON-RPC"] = None
                    else:
                        xbmc.log("service.remove.black.bars.gbm: [TEST] JSON-RPC FAILED (no streamdetails in result)", level=xbmc.LOGDEBUG)
                        results["JSON-RPC"] = None
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    xbmc.log(f"service.remove.black.bars.gbm: [TEST] JSON-RPC FAILED (parse error): {e}", level=xbmc.LOGDEBUG)
                    results["JSON-RPC"] = None
            else:
                xbmc.log("service.remove.black.bars.gbm: [TEST] JSON-RPC FAILED (no result)", level=xbmc.LOGDEBUG)
                results["JSON-RPC"] = None
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: [TEST] JSON-RPC FAILED (exception): {e}", level=xbmc.LOGDEBUG)
            results["JSON-RPC"] = None
        
        # Log summary of all tests
        xbmc.log(f"service.remove.black.bars.gbm: [TEST SUMMARY] Results: {results}", level=xbmc.LOGINFO)
        
        # Return first successful result
        for method, ratio in results.items():
            if ratio is not None:
                xbmc.log(f"service.remove.black.bars.gbm: [TEST] Using {method} with ratio {ratio}", level=xbmc.LOGINFO)
                return ratio
        
        return None


class JsonCacheProvider:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.path = translate_profile_path("cache.json")
        self._cache = {}
        if self.enabled:
            self._ensure_dir()
            self._cache = self._load()

    def _ensure_dir(self):
        try:
            directory = os.path.dirname(self.path)
            if directory:
                # Handle special:// paths
                if directory.startswith("special://"):
                    # Try to translate the path
                    try:
                        directory = xbmc.translatePath(directory)
                    except Exception:
                        pass
                # Create directory if it doesn't exist
                if directory and not os.path.isdir(directory):
                    os.makedirs(directory, exist_ok=True)
                    xbmc.log(f"service.remove.black.bars.gbm: Created cache directory: {directory}", level=xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: Failed to ensure profile dir: " + str(e), level=xbmc.LOGWARNING)

    def _load(self):
        if not self.enabled:
            return {}
        try:
            # Handle special:// paths
            path = self.path
            if path.startswith("special://"):
                try:
                    path = xbmc.translatePath(path)
                except Exception:
                    pass
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                    xbmc.log(f"service.remove.black.bars.gbm: Loaded cache with {len(cache)} entries", level=xbmc.LOGDEBUG)
                    return cache
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: Failed to load cache: " + str(e), level=xbmc.LOGWARNING)
        return {}

    def _save(self):
        if not self.enabled:
            return
        try:
            # Ensure directory exists before saving
            self._ensure_dir()
            # Handle special:// paths
            path = self.path
            if path.startswith("special://"):
                try:
                    path = xbmc.translatePath(path)
                except Exception:
                    pass
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f)
                xbmc.log(f"service.remove.black.bars.gbm: Saved cache with {len(self._cache)} entries", level=xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: Failed to save cache: " + str(e), level=xbmc.LOGWARNING)
    
    def clear(self):
        """Clear the cache"""
        try:
            self._cache = {}
            # Handle special:// paths
            path = self.path
            if path.startswith("special://"):
                try:
                    path = xbmc.translatePath(path)
                except Exception:
                    pass
            if os.path.exists(path):
                os.remove(path)
                xbmc.log("service.remove.black.bars.gbm: Cache cleared", level=xbmc.LOGINFO)
                return True
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: Failed to clear cache: " + str(e), level=xbmc.LOGWARNING)
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


class FileMetadataProvider:
    def is_local_file(self, path):
        return is_local_file(path)

    def extract_from_file(self, path):
        # Optionally parse via mediainfo/ffprobe if available.
        # For now, return None to keep GBM path simple and avoid external deps.
        return None


class IMDbProvider:
    def get_aspect_ratio(self, title, imdb_number=None):
        try:
            value = getOriginalAspectRatio(title, imdb_number=imdb_number)
            if isinstance(value, list):
                # Prefer first value if multiple and no theatrical tag detected upstream
                value = value[0] if value else None
            if value:
                return int(value)
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: IMDbProvider error: " + str(e), level=xbmc.LOGWARNING)
        return None


class ZoomApplier:
    def __init__(self):
        self.last_zoom_time_ms = 0

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

    def _calculate_zoom(self, detected_ratio):
        if detected_ratio > 177:
            return detected_ratio / 177.0
        return 1.0

    def apply_zoom(self, detected_ratio, player):
        try:
            now_ms = int(time.time() * 1000)
            if now_ms - self.last_zoom_time_ms < ZOOM_RATE_LIMIT_MS:
                xbmc.log("service.remove.black.bars.gbm: Zoom rate limited", level=xbmc.LOGDEBUG)
                return False
            if not self._is_video_playing_fullscreen(player):
                xbmc.log("service.remove.black.bars.gbm: Video not playing fullscreen", level=xbmc.LOGDEBUG)
                return False
            zoom_amount = self._calculate_zoom(detected_ratio)
            xbmc.log(f"service.remove.black.bars.gbm: Applying zoom {zoom_amount} for ratio {detected_ratio}", level=xbmc.LOGINFO)
            # Use Player.SetViewMode with zoom parameter
            # viewmode is an object with zoom value (matching old code format)
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
            xbmc.log(f"service.remove.black.bars.gbm: JSONRPC result: {result}", level=xbmc.LOGDEBUG)
            self.last_zoom_time_ms = now_ms
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
        # Initialize cache with enabled setting
        cache_enabled = self._get_cache_enabled()
        self.cache = JsonCacheProvider(enabled=cache_enabled)
        self.filemeta = FileMetadataProvider()
        self.imdb = IMDbProvider()

        if "toggle" in sys.argv:
            if xbmcgui.Window(10000).getProperty("removeblackbars_status") == "on":
                self.show_original()
            else:
                self.on_av_started()
        
        # Check if cache should be cleared (from settings action)
        # This will be handled in main() if called with clear_cache parameter

    def _read_settings(self):
        try:
            enabled = self._addon.getSetting("automatically_execute") == "true"
        except Exception:
            enabled = True
        try:
            imdb_fallback = self._addon.getSetting("enable_imdb_fallback") == "true"
        except Exception:
            imdb_fallback = False
        return enabled, imdb_fallback

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
            imdb_number = xbmc.getInfoLabel("VideoPlayer.IMDBNumber")
            xbmc.log(f"service.remove.black.bars.gbm: [DETECT] Detecting ratio for title={title}, year={year}, imdb={imdb_number}", level=xbmc.LOGDEBUG)

            results = {}  # Store results from all providers

            # 1) IMDb (first priority, cache only IMDb results)
            enabled, imdb_fallback = self._read_settings()
            if imdb_fallback:
                # Try cache first
                xbmc.log("service.remove.black.bars.gbm: [DETECT] Trying IMDb cache", level=xbmc.LOGDEBUG)
                ratio = self.cache.get(title, year, imdb_id=imdb_number if imdb_number else None)
                if ratio:
                    xbmc.log(f"service.remove.black.bars.gbm: [DETECT] IMDb cache SUCCESS: {ratio}", level=xbmc.LOGINFO)
                    results["IMDb cache"] = ratio
                else:
                    xbmc.log("service.remove.black.bars.gbm: [DETECT] IMDb cache FAILED", level=xbmc.LOGDEBUG)
                    results["IMDb cache"] = None
                
                # Try IMDb provider
                xbmc.log("service.remove.black.bars.gbm: [DETECT] Trying IMDb provider", level=xbmc.LOGDEBUG)
                ratio = self.imdb.get_aspect_ratio(title, imdb_number=imdb_number if imdb_number else None)
                if ratio:
                    xbmc.log(f"service.remove.black.bars.gbm: [DETECT] IMDb SUCCESS: {ratio}", level=xbmc.LOGINFO)
                    results["IMDb"] = ratio
                    # Cache IMDb result
                    self.cache.store(title, year, ratio, imdb_id=imdb_number if imdb_number else None)
                else:
                    xbmc.log("service.remove.black.bars.gbm: [DETECT] IMDb FAILED", level=xbmc.LOGDEBUG)
                    results["IMDb"] = None
            else:
                xbmc.log("service.remove.black.bars.gbm: [DETECT] IMDb fallback disabled, skipping", level=xbmc.LOGDEBUG)
                results["IMDb cache"] = None
                results["IMDb"] = None

            # 2) Kodi metadata (includes JSON-RPC in KodiMetadataProvider)
            xbmc.log("service.remove.black.bars.gbm: [DETECT] Trying Kodi metadata provider", level=xbmc.LOGDEBUG)
            ratio = self.kodi.get_aspect_ratio(video_info_tag)
            if ratio:
                xbmc.log(f"service.remove.black.bars.gbm: [DETECT] Kodi metadata SUCCESS: {ratio}", level=xbmc.LOGINFO)
                results["Kodi metadata"] = ratio
            else:
                xbmc.log("service.remove.black.bars.gbm: [DETECT] Kodi metadata FAILED", level=xbmc.LOGDEBUG)
                results["Kodi metadata"] = None

            # 3) Local file metadata
            try:
                path = video_info_tag.getFilenameAndPath()
            except Exception:
                path = None
            if self.filemeta.is_local_file(path):
                xbmc.log(f"service.remove.black.bars.gbm: [DETECT] Trying file metadata provider for {path}", level=xbmc.LOGDEBUG)
                ratio = self.filemeta.extract_from_file(path)
                if ratio:
                    xbmc.log(f"service.remove.black.bars.gbm: [DETECT] File metadata SUCCESS: {ratio}", level=xbmc.LOGINFO)
                    results["File metadata"] = ratio
                else:
                    xbmc.log("service.remove.black.bars.gbm: [DETECT] File metadata FAILED", level=xbmc.LOGDEBUG)
                    results["File metadata"] = None
            else:
                xbmc.log("service.remove.black.bars.gbm: [DETECT] File is not local, skipping file metadata provider", level=xbmc.LOGDEBUG)
                results["File metadata"] = None

            # Log summary of all tests
            xbmc.log(f"service.remove.black.bars.gbm: [DETECT SUMMARY] Results: {results}", level=xbmc.LOGINFO)

            # Return first successful result (in priority order: IMDb cache, IMDb, Kodi metadata, File metadata)
            for provider in ["IMDb cache", "IMDb", "Kodi metadata", "File metadata"]:
                if provider in results and results[provider] is not None:
                    ratio = results[provider]
                    xbmc.log(f"service.remove.black.bars.gbm: [DETECT] Using {provider} with ratio {ratio}", level=xbmc.LOGINFO)
                    return ratio

            xbmc.log("service.remove.black.bars.gbm: [DETECT] No aspect ratio found from any provider", level=xbmc.LOGDEBUG)
            return None
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: detect ratio error: " + str(e), level=xbmc.LOGERROR)
            return None

    def onAVStarted(self):
        # Kodi may call this in older versions
        self.on_av_started()

    def onAVChange(self):
        self.on_av_change()

    def on_av_started(self):
        try:
            xbmc.log("service.remove.black.bars.gbm: on_av_started called", level=xbmc.LOGINFO)
            enabled, _ = self._read_settings()
            xbmc.log(f"service.remove.black.bars.gbm: Automatically execute enabled: {enabled}", level=xbmc.LOGINFO)
            if not enabled:
                xbmcgui.Window(10000).setProperty("removeblackbars_status", "off")
                self.show_original()
                return
            xbmcgui.Window(10000).setProperty("removeblackbars_status", "on")
            ratio = self._detect_aspect_ratio()
            xbmc.log(f"service.remove.black.bars.gbm: Detected aspect ratio: {ratio}", level=xbmc.LOGINFO)
            if ratio:
                self.zoom.apply_zoom(ratio, self)
            else:
                xbmc.log("service.remove.black.bars.gbm: No aspect ratio detected, skipping zoom", level=xbmc.LOGINFO)
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: on_av_started error: " + str(e), level=xbmc.LOGERROR)

    def on_av_change(self):
        try:
            # Re-évaluer le ratio sur changement AV
            enabled, _ = self._read_settings()
            if not enabled:
                return
            ratio = self._detect_aspect_ratio()
            if ratio:
                self.zoom.apply_zoom(ratio, self)
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: on_av_change error: " + str(e), level=xbmc.LOGERROR)

    def onPlayBackStopped(self):
        try:
            xbmcgui.Window(10000).setProperty("removeblackbars_status", "off")
        except Exception:
            pass

    def onPlayBackEnded(self):
        try:
            xbmcgui.Window(10000).setProperty("removeblackbars_status", "off")
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
        addon = xbmcaddon.Addon()
        cache_enabled = addon.getSetting("enable_cache") == "true"
        if not cache_enabled:
            xbmcgui.Dialog().ok("IMDb Cache", "IMDb cache is disabled. Enable it first in settings.")
            return
        cache = JsonCacheProvider(enabled=True)
        if cache.clear():
            xbmcgui.Dialog().ok("IMDb Cache", "IMDb cache cleared successfully.")
        else:
            xbmcgui.Dialog().ok("IMDb Cache", "IMDb cache is already empty or could not be cleared.")
    except Exception as e:
        xbmc.log("service.remove.black.bars.gbm: Error clearing IMDb cache: " + str(e), level=xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", f"Failed to clear IMDb cache: {e}")


def main():
    # Check if called with clear_cache action
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
