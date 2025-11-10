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
        try:
            # Preferred: direct float if available
            if hasattr(video_info_tag, "getVideoAspectRatio"):
                value = video_info_tag.getVideoAspectRatio()
                if value:
                    return int((float(value) + 0.005) * 100)
        except Exception:
            pass
        try:
            label = xbmc.getInfoLabel("VideoPlayer.AspectRatio")
            if not label:
                return None
            # Common formats: "1.78" or "1.78:1"
            cleaned = label.split(":")[0].strip()
            return int((float(cleaned) + 0.005) * 100)
        except Exception:
            return None


class JsonCacheProvider:
    def __init__(self):
        self.path = translate_profile_path("cache.json")
        self._ensure_dir()
        self._cache = self._load()

    def _ensure_dir(self):
        try:
            directory = os.path.dirname(self.path)
            if directory and not os.path.isdir(directory):
                os.makedirs(directory, exist_ok=True)
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: Failed to ensure profile dir: " + str(e), level=xbmc.LOGWARNING)

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: Failed to load cache: " + str(e), level=xbmc.LOGWARNING)
        return {}

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f)
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: Failed to save cache: " + str(e), level=xbmc.LOGWARNING)

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
                return False
            window_id = xbmcgui.getCurrentWindowId()
            if window_id != 12005:
                return False
            if not player.isPlaying():
                return False
            return True
        except Exception:
            return False

    def _calculate_zoom(self, detected_ratio):
        if detected_ratio > 177:
            return detected_ratio / 177.0
        return 1.0

    def apply_zoom(self, detected_ratio, player):
        try:
            now_ms = int(time.time() * 1000)
            if now_ms - self.last_zoom_time_ms < ZOOM_RATE_LIMIT_MS:
                return False
            if not self._is_video_playing_fullscreen(player):
                return False
            zoom_amount = self._calculate_zoom(detected_ratio)
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Player.SetViewMode","params":{"viewmode":{"zoom":' + str(zoom_amount) + '}},"id":1}'
            )
            self.last_zoom_time_ms = now_ms
            if zoom_amount > 1.0:
                notify("Zoom appliqué {:0.2f}".format(zoom_amount))
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
        self.cache = JsonCacheProvider()
        self.filemeta = FileMetadataProvider()
        self.imdb = IMDbProvider()
        self._addon = xbmcaddon.Addon()

        if "toggle" in sys.argv:
            if xbmcgui.Window(10000).getProperty("removeblackbars_status") == "on":
                self.show_original()
            else:
                self.on_av_started()

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
            xbmc.log(f"service.remove.black.bars.gbm: Detecting ratio for title={title}, year={year}, imdb={imdb_number}", level=xbmc.LOGDEBUG)

            # 1) Kodi metadata
            xbmc.log("service.remove.black.bars.gbm: Trying Kodi metadata provider", level=xbmc.LOGDEBUG)
            ratio = self.kodi.get_aspect_ratio(video_info_tag)
            if ratio:
                xbmc.log(f"service.remove.black.bars.gbm: Kodi metadata ratio={ratio}", level=xbmc.LOGINFO)
                self.cache.store(title, year, ratio, imdb_id=imdb_number if imdb_number else None)
                return ratio

            # 2) Cache
            xbmc.log("service.remove.black.bars.gbm: Trying cache provider", level=xbmc.LOGDEBUG)
            ratio = self.cache.get(title, year, imdb_id=imdb_number if imdb_number else None)
            if ratio:
                xbmc.log(f"service.remove.black.bars.gbm: Cache ratio={ratio}", level=xbmc.LOGINFO)
                return ratio

            # 3) Local file metadata
            try:
                path = video_info_tag.getFilenameAndPath()
            except Exception:
                path = None
            if self.filemeta.is_local_file(path):
                xbmc.log(f"service.remove.black.bars.gbm: Trying file metadata provider for {path}", level=xbmc.LOGDEBUG)
                ratio = self.filemeta.extract_from_file(path)
                if ratio:
                    xbmc.log(f"service.remove.black.bars.gbm: File metadata ratio={ratio}", level=xbmc.LOGINFO)
                    self.cache.store(title, year, ratio, imdb_id=imdb_number if imdb_number else None)
                    return ratio
            else:
                xbmc.log("service.remove.black.bars.gbm: File is not local, skipping file metadata provider", level=xbmc.LOGDEBUG)

            # 4) IMDb fallback
            enabled, imdb_fallback = self._read_settings()
            if imdb_fallback:
                xbmc.log("service.remove.black.bars.gbm: Trying IMDb provider", level=xbmc.LOGDEBUG)
                ratio = self.imdb.get_aspect_ratio(title, imdb_number=imdb_number if imdb_number else None)
                if ratio:
                    xbmc.log(f"service.remove.black.bars.gbm: IMDb ratio={ratio}", level=xbmc.LOGINFO)
                    self.cache.store(title, year, ratio, imdb_id=imdb_number if imdb_number else None)
                    return ratio
            else:
                xbmc.log("service.remove.black.bars.gbm: IMDb fallback disabled, skipping", level=xbmc.LOGDEBUG)

            xbmc.log("service.remove.black.bars.gbm: No aspect ratio found from any provider", level=xbmc.LOGDEBUG)
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
            enabled, _ = self._read_settings()
            if not enabled:
                xbmcgui.Window(10000).setProperty("removeblackbars_status", "off")
                self.show_original()
                return
            xbmcgui.Window(10000).setProperty("removeblackbars_status", "on")
            ratio = self._detect_aspect_ratio()
            if ratio:
                self.zoom.apply_zoom(ratio, self)
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
            xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.SetViewMode","params":{"viewmode":{"zoom":1.0}},"id":1}')
            notify("Affichage original")
        except Exception as e:
            xbmc.log("service.remove.black.bars.gbm: show_original error: " + str(e), level=xbmc.LOGERROR)


def main():
    service = Service()
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break


if __name__ == "__main__":
    main()
