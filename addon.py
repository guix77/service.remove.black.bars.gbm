import os
import sys
import json
import time
import math

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

# Ratio validation constants
MIN_VALID_RATIO = 100  # 1.00:1 (square)
MAX_VALID_RATIO = 500  # 5.00:1 (very wide)


def notify(msg, duration_ms=None):
    """
    Show notification with configurable duration.
    
    Args:
        msg: Message to display
        duration_ms: Duration in milliseconds (if None, uses setting, default: 2000ms)
    """
    if duration_ms is None:
        # Get duration from settings (default: 2000ms)
        try:
            addon = xbmcaddon.Addon()
            setting_value = addon.getSetting("notification_duration")
            if setting_value:
                duration_ms = int(setting_value)
            else:
                duration_ms = 2000
        except Exception:
            duration_ms = 2000
    # Kodi notification() time parameter expects milliseconds (default: 5000ms)
    xbmcgui.Dialog().notification("Remove Black Bars (GBM)", msg, None, duration_ms)


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
    def get_aspect_ratio(self, video_info_tag, reason=None, player=None):
        """
        Get aspect ratio from Kodi metadata using JSON-RPC Player.GetItem with streamdetails.
        Calculates ratio from actual video resolution (width/height).
        Retries up to 3 times with small delays if resolution is not immediately available.
        
        Returns aspect ratio as integer (e.g., 178 for 16:9, 240 for 2.40:1).
        Returns None if resolution cannot be obtained.
        
        Args:
            video_info_tag: Video info tag (unused but kept for compatibility)
            reason: Optional reason string to include in log message
            player: xbmc.Player instance (unused, kept for compatibility)
        """
        try:
            reason_text = f" ({reason})" if reason else ""
            
            # Retry up to 8 times with increasing delays (resolution may not be available immediately)
            max_retries = 8
            base_delay_ms = 300  # Start with 300ms, increase with each retry
            
            # Add initial delay before first attempt (streamdetails may not be ready immediately)
            xbmc.sleep(100)
            
            for attempt in range(max_retries):
                if attempt > 0:
                    # Wait progressively longer before retrying
                    delay = base_delay_ms * attempt
                    xbmc.log(f"service.remove.black.bars.gbm: Retry {attempt + 1}/{max_retries} to get file_ratio{reason_text} (waiting {delay}ms)", level=xbmc.LOGDEBUG)
                    xbmc.sleep(delay)
                else:
                    xbmc.log(f"service.remove.black.bars.gbm: Attempt {attempt + 1}/{max_retries} to get file_ratio{reason_text}", level=xbmc.LOGDEBUG)
                
                # Get resolution using JSON-RPC Player.GetItem with streamdetails
                json_cmd = json.dumps({
                    "jsonrpc": "2.0",
                    "method": "Player.GetItem",
                    "params": {
                        "playerid": 1,
                        "properties": ["streamdetails"]
                    },
                    "id": 1
                })
                result = xbmc.executeJSONRPC(json_cmd)
                if result:
                    result_json = json.loads(result)
                    # Check for errors first
                    if "error" in result_json:
                        error_msg = result_json.get("error", {}).get("message", "Unknown error")
                        error_code = result_json.get("error", {}).get("code", "?")
                        if attempt == max_retries - 1:
                            xbmc.log(f"service.remove.black.bars.gbm: JSON-RPC error after {max_retries} attempts{reason_text}: [{error_code}] {error_msg}", level=xbmc.LOGDEBUG)
                        continue
                    # Extract width/height from streamdetails.video[0]
                    if "result" in result_json and "item" in result_json["result"]:
                        item = result_json["result"]["item"]
                        if "streamdetails" in item:
                            if "video" in item["streamdetails"]:
                                video_streams = item["streamdetails"]["video"]
                                if video_streams and len(video_streams) > 0:
                                    video_stream = video_streams[0]
                                    if "width" in video_stream and "height" in video_stream:
                                        width = video_stream["width"]
                                        height = video_stream["height"]
                                        if width and height and width > 0 and height > 0:
                                            ratio = int((width / float(height)) * 100)
                                            # Validate ratio
                                            if MIN_VALID_RATIO <= ratio <= MAX_VALID_RATIO:
                                                if attempt > 0:
                                                    xbmc.log(f"service.remove.black.bars.gbm: Calculated from resolution via JSON-RPC{reason_text}: {width}x{height} = {ratio} (after {attempt + 1} attempts)", level=xbmc.LOGDEBUG)
                                                else:
                                                    xbmc.log(f"service.remove.black.bars.gbm: Calculated from resolution via JSON-RPC{reason_text}: {width}x{height} = {ratio}", level=xbmc.LOGDEBUG)
                                                return ratio
                                            else:
                                                xbmc.log(f"service.remove.black.bars.gbm: Invalid ratio from resolution: {ratio} ({width}x{height})", level=xbmc.LOGDEBUG)
                                                break  # Don't retry if ratio is invalid
                                    else:
                                        if attempt == max_retries - 1:
                                            xbmc.log(f"service.remove.black.bars.gbm: JSON-RPC streamdetails.video[0] missing width/height after {max_retries} attempts{reason_text}. Video stream keys: {list(video_stream.keys())}", level=xbmc.LOGDEBUG)
                                else:
                                    if attempt == max_retries - 1:
                                        xbmc.log(f"service.remove.black.bars.gbm: JSON-RPC streamdetails.video is empty after {max_retries} attempts{reason_text}", level=xbmc.LOGDEBUG)
                            else:
                                if attempt == max_retries - 1:
                                    xbmc.log(f"service.remove.black.bars.gbm: JSON-RPC streamdetails missing 'video' key after {max_retries} attempts{reason_text}. Streamdetails keys: {list(item['streamdetails'].keys())}", level=xbmc.LOGDEBUG)
                        else:
                            if attempt == max_retries - 1:
                                # Last attempt failed, log the full result for debugging
                                item_keys = list(item.keys()) if item else []
                                xbmc.log(f"service.remove.black.bars.gbm: JSON-RPC returned no streamdetails after {max_retries} attempts{reason_text}. Item keys: {item_keys}", level=xbmc.LOGDEBUG)
                    elif attempt == max_retries - 1:
                        # Last attempt failed, log the full result for debugging
                        result_keys = list(result_json.get('result', {}).keys()) if 'result' in result_json else []
                        xbmc.log(f"service.remove.black.bars.gbm: JSON-RPC returned no 'item' after {max_retries} attempts{reason_text}. Result keys: {result_keys}", level=xbmc.LOGDEBUG)
                elif attempt == max_retries - 1:
                    # Last attempt failed, log the error
                    xbmc.log(f"service.remove.black.bars.gbm: JSON-RPC returned no result after {max_retries} attempts{reason_text}", level=xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: Error getting resolution via JSON-RPC{reason_text}: {e}", level=xbmc.LOGDEBUG)
        
        # Log final failure with more details
        xbmc.log(f"service.remove.black.bars.gbm: Failed to get file_ratio after {max_retries} attempts{reason_text}. This will cause incorrect zoom calculation if encoded black bars are present!", level=xbmc.LOGDEBUG)
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
            if value is not None:
                ratio = int(value)
                # Validate cached ratio
                if ratio < MIN_VALID_RATIO or ratio > MAX_VALID_RATIO:
                    xbmc.log(f"service.remove.black.bars.gbm: Invalid cached ratio: {ratio} for key '{key}' (valid range: {MIN_VALID_RATIO}-{MAX_VALID_RATIO})", level=xbmc.LOGWARNING)
                    return None
                return ratio
            return None
        except Exception:
            return None

    def store(self, title, year, ratio, imdb_id=None):
        try:
            # Validate ratio before storing
            if ratio is None:
                return
            ratio_int = int(ratio)
            if ratio_int < MIN_VALID_RATIO or ratio_int > MAX_VALID_RATIO:
                xbmc.log(f"service.remove.black.bars.gbm: Invalid ratio to store: {ratio_int} (valid range: {MIN_VALID_RATIO}-{MAX_VALID_RATIO})", level=xbmc.LOGWARNING)
                return
            key = self._make_key(title, year, imdb_id)
            self._cache[key] = ratio_int
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
                ratio = int(value)
                # Validate IMDb ratio
                if ratio < MIN_VALID_RATIO or ratio > MAX_VALID_RATIO:
                    xbmc.log(f"service.remove.black.bars.gbm: Invalid IMDb ratio: {ratio} for '{title}' (valid range: {MIN_VALID_RATIO}-{MAX_VALID_RATIO})", level=xbmc.LOGWARNING)
                    return None
                return ratio
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

    def _validate_ratio(self, ratio, ratio_name="ratio"):
        """
        Validate that ratio is within acceptable range.
        
        Args:
            ratio: Aspect ratio to validate
            ratio_name: Name for logging (e.g., "detected_ratio", "file_ratio")
        
        Returns:
            True if valid, False otherwise
        """
        if ratio is None:
            return False
        if not isinstance(ratio, (int, float)):
            xbmc.log(f"service.remove.black.bars.gbm: Invalid {ratio_name} type: {type(ratio)}", level=xbmc.LOGWARNING)
            return False
        if ratio < MIN_VALID_RATIO or ratio > MAX_VALID_RATIO:
            xbmc.log(f"service.remove.black.bars.gbm: Invalid {ratio_name} value: {ratio} (valid range: {MIN_VALID_RATIO}-{MAX_VALID_RATIO})", level=xbmc.LOGWARNING)
            return False
        return True

    def _get_16_9_tolerance(self, player):
        """
        Get 16:9 tolerance range from settings.
        
        Args:
            player: Service instance to access settings (can be None)
        
        Returns:
            Tuple (min, max) tolerance values
        """
        try:
            if player and hasattr(player, '_addon'):
                min_val = int(player._addon.getSetting("tolerance_16_9_min") or "175")
                max_val = int(player._addon.getSetting("tolerance_16_9_max") or "180")
            else:
                min_val = 175
                max_val = 180
            # Ensure min <= max
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            return (min_val, max_val)
        except Exception:
            return (175, 180)  # Default values

    def _round_to_0_01(self, value):
        """
        Arrondit vers le haut à 0.01 près.
        Exemple: 1.3333 -> 1.34, 1.3308 -> 1.34, 1.3616 -> 1.37
        """
        return math.ceil(value * 100) / 100.0

    def _calculate_zoom(self, detected_ratio, zoom_narrow_ratios=False, file_ratio=None, player=None):
        """
        Calculate zoom amount based on detected ratio.
        
        Args:
            detected_ratio: The detected content aspect ratio (e.g., from IMDb)
            zoom_narrow_ratios: Whether to zoom narrow ratios (< 16:9)
            file_ratio: Optional file aspect ratio (may include encoded black bars)
                       If provided and different from detected_ratio, use it for zoom calculation
            player: Service instance (optional, for accessing settings)
        """
        # Validate detected_ratio
        if not self._validate_ratio(detected_ratio, "detected_ratio"):
            return 1.0
        
        # Validate file_ratio if provided
        if file_ratio is not None and not self._validate_ratio(file_ratio, "file_ratio"):
            file_ratio = None
        
        # Get 16:9 tolerance from settings
        tolerance_min, tolerance_max = self._get_16_9_tolerance(player)
        
        # If file_ratio == detected_ratio AND within 16:9 tolerance, no zoom needed
        # (no encoded bars, and no display bars if it's 16:9)
        if file_ratio and file_ratio == detected_ratio and tolerance_min <= file_ratio <= tolerance_max:
            return 1.0
        
        # If file_ratio is provided and different from detected_ratio, use it for zoom calculation
        if file_ratio and file_ratio != detected_ratio:
            # Check if neither file nor content is close to 16:9
            # In this case, use file_ratio directly (file/177 or 177/file) instead of combined zoom
            file_is_16_9 = tolerance_min <= file_ratio <= tolerance_max
            content_is_16_9 = tolerance_min <= detected_ratio <= tolerance_max
            
            if not file_is_16_9 and not content_is_16_9:
                # Neither close to 16:9: use file_ratio directly as reference
                if file_ratio > 177:
                    direct_zoom = file_ratio / 177.0
                    xbmc.log(f"service.remove.black.bars.gbm: Using file_ratio directly (wide): file_ratio={file_ratio}, zoom={direct_zoom:.4f}", level=xbmc.LOGDEBUG)
                else:
                    direct_zoom = 177.0 / file_ratio
                    xbmc.log(f"service.remove.black.bars.gbm: Using file_ratio directly (narrow): file_ratio={file_ratio}, zoom={direct_zoom:.4f}", level=xbmc.LOGDEBUG)
                return self._round_to_0_01(direct_zoom)
            
            # Otherwise, calculate combined zoom (encoded bars + display bars)
            # This handles both encoded black bars and cases where file format differs from content
            # We need to combine:
            # 1. Zoom to remove encoded black bars (file_ratio -> detected_ratio)
            # 2. Zoom to remove display black bars (detected_ratio -> 177 for wide ratios)
            if file_ratio > detected_ratio:
                # File is wider than content: horizontal encoded bars, need to zoom in (file_ratio / detected_ratio)
                encoded_zoom = file_ratio / float(detected_ratio)
            else:
                # File is narrower than content: vertical encoded bars, need to zoom in (detected_ratio / file_ratio)
                encoded_zoom = detected_ratio / float(file_ratio)
            
            xbmc.log(f"service.remove.black.bars.gbm: File ratio differs: file_ratio={file_ratio}, detected_ratio={detected_ratio}, encoded_zoom={encoded_zoom:.4f}", level=xbmc.LOGDEBUG)
            
            # Check if we need additional zoom for display black bars
            # Only if detected_ratio is NOT within 16:9 tolerance
            if tolerance_min <= detected_ratio <= tolerance_max:
                # Content is 16:9, no display zoom needed
                xbmc.log(f"service.remove.black.bars.gbm: Encoded zoom only: {encoded_zoom:.4f} (content is 16:9, no display bars)", level=xbmc.LOGDEBUG)
                return self._round_to_0_01(encoded_zoom)
            elif detected_ratio > tolerance_max:
                # Content is wider than 16:9, need additional zoom for display bars
                # Special case: if file_ratio is exactly 16:9 (177) and detected_ratio is around 185
                # Use geometric mean of direct zoom and combined zoom for better accuracy
                # Geometric mean: sqrt(zoom_direct * zoom_combined)
                # This handles cases like "Superman" where file_ratio=177 (exactly 16:9) and detected_ratio=185
                # Justification: geometric mean gives the zoom that, when applied, produces the same result
                # as applying direct zoom and combined zoom in sequence
                if file_is_16_9 and file_ratio == 177 and 180 <= detected_ratio <= 190:
                    # Use geometric mean for file_ratio exactly 16:9 (177) and detected_ratio around 185
                    import math
                    zoom_direct = detected_ratio / 177.0
                    zoom_combined = encoded_zoom * (detected_ratio / 177.0)
                    geometric_mean_zoom = math.sqrt(zoom_direct * zoom_combined)
                    xbmc.log(f"service.remove.black.bars.gbm: Geometric mean zoom for file_ratio exactly 16:9: direct={zoom_direct:.4f}, combined={zoom_combined:.4f}, geometric={geometric_mean_zoom:.4f} (file_ratio={file_ratio}, detected_ratio={detected_ratio})", level=xbmc.LOGDEBUG)
                    if geometric_mean_zoom < 1.0:
                        xbmc.log(f"service.remove.black.bars.gbm: ERROR: Invalid zoom < 1.0 calculated: {geometric_mean_zoom:.4f}", level=xbmc.LOGERROR)
                        return 1.0
                    return self._round_to_0_01(geometric_mean_zoom)
                else:
                    # Standard calculation: use 177 as reference
                    display_zoom = detected_ratio / 177.0
                    total_zoom = encoded_zoom * display_zoom
                    if total_zoom < 1.0:
                        xbmc.log(f"service.remove.black.bars.gbm: ERROR: Invalid zoom < 1.0 calculated: encoded={encoded_zoom:.4f}, display={display_zoom:.4f}, total={total_zoom:.4f}, file_ratio={file_ratio}, detected_ratio={detected_ratio}, tolerance=({tolerance_min}-{tolerance_max})", level=xbmc.LOGERROR)
                        return 1.0
                    xbmc.log(f"service.remove.black.bars.gbm: Combined zoom: encoded={encoded_zoom:.4f}, display={display_zoom:.4f}, total={total_zoom:.4f}", level=xbmc.LOGDEBUG)
                    return self._round_to_0_01(total_zoom)
            elif zoom_narrow_ratios and detected_ratio < tolerance_min:
                # Content is narrower than 16:9, and zoom_narrow_ratios is enabled
                display_zoom = 177.0 / detected_ratio
                total_zoom = encoded_zoom * display_zoom
                if total_zoom < 1.0:
                    xbmc.log(f"service.remove.black.bars.gbm: ERROR: Invalid zoom < 1.0 calculated: encoded={encoded_zoom:.4f}, display={display_zoom:.4f}, total={total_zoom:.4f}, file_ratio={file_ratio}, detected_ratio={detected_ratio}, tolerance=({tolerance_min}-{tolerance_max})", level=xbmc.LOGERROR)
                    return 1.0
                xbmc.log(f"service.remove.black.bars.gbm: Combined zoom: encoded={encoded_zoom:.4f}, display={display_zoom:.4f}, total={total_zoom:.4f}", level=xbmc.LOGDEBUG)
                return self._round_to_0_01(total_zoom)
            else:
                # No additional zoom needed for display bars (narrow ratios disabled)
                xbmc.log(f"service.remove.black.bars.gbm: Encoded zoom only: {encoded_zoom:.4f} (narrow ratios disabled)", level=xbmc.LOGDEBUG)
                return self._round_to_0_01(encoded_zoom)
        
        # Normal zoom calculation (no encoded black bars)
        # If file_ratio is available and close to 16:9, no need to zoom
        # (file is already 16:9, content fits without black bars)
        if file_ratio and tolerance_min <= file_ratio <= tolerance_max:
            xbmc.log(f"service.remove.black.bars.gbm: No zoom needed: file_ratio={file_ratio} within 16:9 tolerance ({tolerance_min}-{tolerance_max})", level=xbmc.LOGDEBUG)
            return 1.0
        
        # Log when file_ratio is None (important for debugging)
        if file_ratio is None:
            xbmc.log(f"service.remove.black.bars.gbm: Calculating zoom without file_ratio (detected_ratio={detected_ratio}). This may be incorrect if encoded black bars are present!", level=xbmc.LOGDEBUG)
        
        # Calculate zoom for display black bars only
        if detected_ratio > 177:
            display_zoom = detected_ratio / 177.0
            xbmc.log(f"service.remove.black.bars.gbm: Display bars only (wide): detected_ratio={detected_ratio}, zoom={display_zoom:.4f}", level=xbmc.LOGDEBUG)
            return self._round_to_0_01(display_zoom)
        elif zoom_narrow_ratios and detected_ratio < 177:
            display_zoom = 177.0 / detected_ratio
            xbmc.log(f"service.remove.black.bars.gbm: Display bars only (narrow): detected_ratio={detected_ratio}, zoom={display_zoom:.4f}", level=xbmc.LOGDEBUG)
            return self._round_to_0_01(display_zoom)
        xbmc.log(f"service.remove.black.bars.gbm: No zoom needed: detected_ratio={detected_ratio} (no bars to remove)", level=xbmc.LOGDEBUG)
        return 1.0

    def apply_zoom(self, detected_ratio, player, zoom_narrow_ratios=False, file_ratio=None, title=None):
        """
        Apply zoom to remove black bars.
        
        Args:
            detected_ratio: The detected aspect ratio
            player: Service instance (xbmc.Player) with _set_zoom method
            zoom_narrow_ratios: Whether to zoom narrow ratios
            file_ratio: Optional file aspect ratio for encoded black bars
            title: Optional title for logging
        """
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
            zoom_amount = self._calculate_zoom(detected_ratio, zoom_narrow_ratios, file_ratio, player)
            title_display = title or "video"
            xbmc.log(f"service.remove.black.bars.gbm: Applying zoom {zoom_amount:.2f} on {title_display} to remove black bars", level=xbmc.LOGINFO)
            if file_ratio and file_ratio != detected_ratio:
                xbmc.log(f"service.remove.black.bars.gbm: Zoom calculation: file_ratio={file_ratio}, detected_ratio={detected_ratio}, zoom={zoom_amount:.4f}", level=xbmc.LOGDEBUG)
            elif file_ratio is None:
                xbmc.log(f"service.remove.black.bars.gbm: Zoom calculation: file_ratio=None (not available), detected_ratio={detected_ratio}, zoom={zoom_amount:.4f} (may be incorrect if encoded black bars present)", level=xbmc.LOGDEBUG)
            else:
                xbmc.log(f"service.remove.black.bars.gbm: Zoom calculation: file_ratio={file_ratio} (same as detected_ratio), detected_ratio={detected_ratio}, zoom={zoom_amount:.4f}", level=xbmc.LOGDEBUG)
            
            # Set zoom via player's _set_zoom method
            if not player._set_zoom(zoom_amount):
                xbmc.log("service.remove.black.bars.gbm: Failed to set zoom", level=xbmc.LOGWARNING)
            self.last_zoom_time_ms = now_ms
            self.last_applied_ratio = detected_ratio
            if zoom_amount > 1.0:
                msg = "Zoom {:.2f}x applied".format(zoom_amount)
                xbmc.log(f"service.remove.black.bars.gbm: Showing notification: '{msg}'", level=xbmc.LOGDEBUG)
                notify(msg)
            else:
                msg = "No zoom needed"
                xbmc.log(f"service.remove.black.bars.gbm: Showing notification: '{msg}'", level=xbmc.LOGDEBUG)
                notify(msg)
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

    def _set_zoom(self, zoom_amount):
        """
        Set zoom level via JSON-RPC Player.SetViewMode.
        
        Args:
            zoom_amount: Zoom level (1.0 = no zoom, >1.0 = zoom in)
        
        Returns:
            True if successful, False otherwise
        """
        try:
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
                        return False
                except Exception:
                    pass
            return True
        except Exception as e:
            xbmc.log(f"service.remove.black.bars.gbm: _set_zoom error: {e}", level=xbmc.LOGERROR)
            return False

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
            xbmc.log(f"service.remove.black.bars.gbm: Detection: title='{title}', year={year}, imdb_id={imdb_number}", level=xbmc.LOGDEBUG)

            # 1) IMDb (first priority, cache only IMDb results)
            imdb_enabled, _ = self._read_settings()
            imdb_ratio = None
            file_ratio = None
            file_ratio_detected = None  # Always store detected file_ratio for logging, even if not used
            encoded_black_bars_detected = False
            
            if imdb_enabled:
                # Try cache first (use IMDb number if available for more precise cache key)
                imdb_ratio = self.cache.get(title, year, imdb_id=imdb_number)
                if imdb_ratio:
                    xbmc.log(f"service.remove.black.bars.gbm: IMDb cache hit: imdb_ratio={imdb_ratio}", level=xbmc.LOGDEBUG)
                else:
                    xbmc.log("service.remove.black.bars.gbm: IMDb cache miss, querying API", level=xbmc.LOGDEBUG)
                    imdb_ratio = self.imdb.get_aspect_ratio(title, imdb_number=imdb_number)
                    if imdb_ratio:
                        xbmc.log(f"service.remove.black.bars.gbm: IMDb API result: imdb_ratio={imdb_ratio}", level=xbmc.LOGDEBUG)
                        self.cache.store(title, year, imdb_ratio, imdb_id=imdb_number)
                    else:
                        xbmc.log("service.remove.black.bars.gbm: IMDb API: no ratio found", level=xbmc.LOGDEBUG)
                
                # If we have IMDb ratio, get file ratio for encoded black bars detection
                # NOTE: We only use file_ratio if it's very close to 16:9 (likely encoded bars)
                # Otherwise, differences can be due to encoding/container issues, not actual encoded bars
                if imdb_ratio:
                    file_ratio_temp = self.kodi.get_aspect_ratio(video_info_tag, reason="for encoded black bars detection", player=self)
                    if file_ratio_temp:
                        file_ratio_detected = file_ratio_temp  # Always store for logging
                        xbmc.log(f"service.remove.black.bars.gbm: file_ratio retrieved: {file_ratio_temp} (imdb_ratio={imdb_ratio})", level=xbmc.LOGDEBUG)
                    else:
                        xbmc.log(f"service.remove.black.bars.gbm: file_ratio is None (imdb_ratio={imdb_ratio}). Zoom calculation will use detected_ratio only, may be incorrect!", level=xbmc.LOGDEBUG)
                    if file_ratio_temp:
                        difference = abs(file_ratio_temp - imdb_ratio)
                        threshold = max(5, int(imdb_ratio * 0.05))  # 5% of IMDb ratio, minimum 5
                        
                        # Use file_ratio if:
                        # 1. Difference is significant (> threshold) AND (file_ratio is close to 16:9 OR content is close to 16:9)
                        #    → Encoded black bars or cases like Invasion
                        # 2. Difference exists (> 0) AND neither file nor content is close to 16:9
                        #    → Cases like Basil/Le Baron Rouge/The Artist where file_ratio should be used directly
                        tolerance_min, tolerance_max = self.zoom._get_16_9_tolerance(self)
                        file_is_16_9 = tolerance_min <= file_ratio_temp <= tolerance_max
                        content_is_16_9 = tolerance_min <= imdb_ratio <= tolerance_max
                        
                        if difference >= threshold and (file_is_16_9 or content_is_16_9):
                            # Case 1: Encoded black bars or content/file close to 16:9
                            file_ratio = file_ratio_temp
                            if file_is_16_9 and not content_is_16_9:
                                xbmc.log(f"service.remove.black.bars.gbm: Encoded black bars detected: imdb_ratio={imdb_ratio}, file_ratio={file_ratio}, diff={difference}, threshold={threshold}", level=xbmc.LOGDEBUG)
                            else:
                                xbmc.log(f"service.remove.black.bars.gbm: File ratio differs: imdb_ratio={imdb_ratio}, file_ratio={file_ratio}, diff={difference}, threshold={threshold}", level=xbmc.LOGDEBUG)
                        elif difference > 0 and not file_is_16_9 and not content_is_16_9:
                            # Case 2: Neither close to 16:9, use file_ratio directly for zoom calculation
                            file_ratio = file_ratio_temp
                            xbmc.log(f"service.remove.black.bars.gbm: Using file_ratio directly: imdb_ratio={imdb_ratio}, file_ratio={file_ratio}, diff={difference}", level=xbmc.LOGDEBUG)
                        elif file_is_16_9 and imdb_ratio > tolerance_max and difference > 0:
                            # Case 3: file_ratio is exactly 16:9 (or very close) and content is wide
                            # Use file_ratio even if diff < threshold for better zoom calculation
                            file_ratio = file_ratio_temp
                            xbmc.log(f"service.remove.black.bars.gbm: Using file_ratio (16:9) for wide content: imdb_ratio={imdb_ratio}, file_ratio={file_ratio}, diff={difference}, threshold={threshold}", level=xbmc.LOGDEBUG)
                        else:
                            # Don't use file_ratio if conditions not met
                            file_ratio = None
                            if difference >= threshold:
                                xbmc.log(f"service.remove.black.bars.gbm: Difference detected but conditions not met: imdb_ratio={imdb_ratio}, file_ratio={file_ratio_temp}, diff={difference}, threshold={threshold}", level=xbmc.LOGDEBUG)
                            else:
                                xbmc.log(f"service.remove.black.bars.gbm: No significant difference: imdb_ratio={imdb_ratio}, file_ratio={file_ratio_temp}, diff={difference}, threshold={threshold}", level=xbmc.LOGDEBUG)

            # 2) Kodi metadata (fallback if IMDb unavailable or not found)
            if not imdb_ratio:
                xbmc.log("service.remove.black.bars.gbm: IMDb unavailable, using Kodi metadata fallback", level=xbmc.LOGDEBUG)
                file_ratio = self.kodi.get_aspect_ratio(video_info_tag, reason="for ratio detection", player=self)
                if file_ratio:
                    file_ratio_detected = file_ratio
                    xbmc.log(f"service.remove.black.bars.gbm: Kodi metadata: file_ratio={file_ratio}", level=xbmc.LOGDEBUG)

            # Return tuple (detected_ratio, file_ratio, title_display)
            # detected_ratio is IMDb ratio if available, otherwise file_ratio
            # file_ratio is set if available (for zoom calculation, even if no encoded black bars)
            # Note: Even if file_ratio is close to 16:9 and is the real content ratio (no encoded bars),
            # we still use imdb_ratio as detected_ratio and pass file_ratio to zoom calculation
            # This allows the zoom calculation to handle the case properly
            detected_ratio = imdb_ratio if imdb_ratio else file_ratio
            if detected_ratio:
                source = "IMDb" if imdb_ratio else "Kodi metadata"
                xbmc.log(f"service.remove.black.bars.gbm: Detection complete: detected_ratio={detected_ratio} from {source}", level=xbmc.LOGDEBUG)
                
                # Log JSONL line for CASES.jsonl (INFO level so it's always visible)
                try:
                    # Determine media type
                    media_type = video_info_tag.getMediaType() if video_info_tag else None
                    if media_type == "episode":
                        case_type = "series"
                    elif media_type == "movie":
                        case_type = "movie"
                    else:
                        case_type = "movie"  # Default fallback
                    
                    # Build JSONL case entry (without ideal_zoom, to be filled manually)
                    # Use file_ratio_detected if file_ratio is None (for logging purposes)
                    file_ratio_for_log = file_ratio if file_ratio is not None else file_ratio_detected
                    case_data = {
                        "title": title,
                        "year": year,
                        "type": case_type,
                        "imdb_id": imdb_number,
                        "imdb_ratio": imdb_ratio,
                        "file_ratio": file_ratio_for_log,
                        "ideal_zoom": None  # To be filled manually
                    }
                    # Format compact JSON (no spaces) to match CASES.jsonl format
                    jsonl_line = json.dumps(case_data, ensure_ascii=False, separators=(',', ':'))
                    xbmc.log(f"service.remove.black.bars.gbm: CASES.jsonl entry (copy-paste ready, fill ideal_zoom manually): {jsonl_line}", level=xbmc.LOGINFO)
                except Exception as e:
                    xbmc.log(f"service.remove.black.bars.gbm: Error formatting JSONL case entry: {e}", level=xbmc.LOGDEBUG)
                
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
            self._set_zoom(1.0)
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
