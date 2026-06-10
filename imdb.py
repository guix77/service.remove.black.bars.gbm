import json
import re
import requests

import xbmc
import xbmcaddon
import xbmcgui

_GRAPHQL_URL = "https://graphql.imdb.com/"
_SUGGEST_URL = "https://sg.media-imdb.com/suggests/{}/{}.json"
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
    'Content-Type': 'application/json',
}
_GRAPHQL_QUERY = 'query { title(id: "%s") { technicalSpecifications { aspectRatios { items { aspectRatio } } } } }'


def notify(msg):
    try:
        addon = xbmcaddon.Addon()
        setting_value = addon.getSetting("notification_duration")
        duration_ms = int(setting_value) if setting_value else 2000
    except Exception:
        duration_ms = 2000
    xbmcgui.Dialog().notification("Remove Black Bars (GBM)", msg, None, duration_ms)


def _parse_aspect_ratio(aspect_ratio_text):
    """
    Parse aspect ratio text and return as integer (e.g., 178 for 16:9).
    Handles formats like "16:9", "1.85 : 1", "2.35", etc.
    Returns None if parsing fails.
    """
    if not aspect_ratio_text:
        return None
    try:
        text = aspect_ratio_text.strip()
        text = text.split()[0] if text.split() else text
        if ':' in text:
            parts = text.split(':')
            if len(parts) == 2:
                try:
                    num = float(parts[0].strip())
                    den = float(parts[1].strip())
                    if den > 0:
                        return int((num / den + 0.005) * 100)
                except (ValueError, ZeroDivisionError):
                    return None
        else:
            try:
                return int((float(text) + 0.005) * 100)
            except ValueError:
                return None
    except Exception:
        return None
    return None


def _normalize_imdb_id(imdb_number):
    if not imdb_number:
        return None
    s = str(imdb_number).strip()
    if s.isdigit():
        return "tt" + s
    if not s.startswith("tt"):
        return "tt" + s
    return s


def _fetch_ratios_graphql(imdb_id):
    """Fetch aspect ratios from IMDb GraphQL API. Returns list of ratio strings or None."""
    query = _GRAPHQL_QUERY % imdb_id
    try:
        resp = requests.post(_GRAPHQL_URL, headers=_HEADERS, json={"query": query}, timeout=10)
        resp.raise_for_status()
        items = (resp.json()
                 .get("data", {})
                 .get("title", {})
                 .get("technicalSpecifications", {})
                 .get("aspectRatios", {})
                 .get("items", []))
        ratios = []
        for item in items:
            parsed = _parse_aspect_ratio(item.get("aspectRatio", ""))
            if parsed:
                ratios.append(str(parsed))
        if ratios:
            xbmc.log(f"service.remove.black.bars.gbm: [IMDb] GraphQL ratios for {imdb_id}: {ratios}", level=xbmc.LOGDEBUG)
        return ratios if ratios else None
    except Exception as e:
        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] GraphQL error for {imdb_id}: {e}", level=xbmc.LOGWARNING)
        return None


def _search_imdb_id(title):
    """Search IMDb ID by title using suggest API. Returns imdb_id string or None."""
    if not title:
        return None
    try:
        query = title.lower().strip()
        first_char = query[0] if query else 'a'
        encoded = requests.utils.quote(query)
        url = _SUGGEST_URL.format(first_char, encoded)
        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Suggest search: {url}", level=xbmc.LOGDEBUG)
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        # Strip JSONP wrapper: imdb$query({...})
        m = re.match(r'^[^(]+\((.+)\)\s*$', resp.text.strip(), re.DOTALL)
        if not m:
            xbmc.log("service.remove.black.bars.gbm: [IMDb] Suggest: unexpected response format", level=xbmc.LOGWARNING)
            return None
        results = json.loads(m.group(1)).get("d", [])
        if results:
            found_id = results[0].get("id")
            xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Suggest found: {found_id} for '{title}'", level=xbmc.LOGDEBUG)
            return found_id
    except Exception as e:
        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Suggest search error: {e}", level=xbmc.LOGWARNING)
    return None


def getOriginalAspectRatio(title, imdb_number=None):
    """
    Fetch aspect ratio from IMDb GraphQL API.
    Returns a string (e.g. "239"), a list of strings, or None.
    """
    try:
        imdb_id = _normalize_imdb_id(imdb_number)

        if imdb_id:
            xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Querying GraphQL for {imdb_id}", level=xbmc.LOGDEBUG)
            ratios = _fetch_ratios_graphql(imdb_id)
            if ratios:
                xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Aspect ratio(s): {ratios}", level=xbmc.LOGINFO)
                return ratios[0] if len(ratios) == 1 else ratios

        if title:
            xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Falling back to title search: '{title}'", level=xbmc.LOGDEBUG)
            found_id = _search_imdb_id(title)
            if found_id:
                ratios = _fetch_ratios_graphql(found_id)
                if ratios:
                    xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Aspect ratio(s) via title search: {ratios}", level=xbmc.LOGINFO)
                    return ratios[0] if len(ratios) == 1 else ratios

        xbmc.log("service.remove.black.bars.gbm: [IMDb] No aspect ratio found", level=xbmc.LOGWARNING)
        return None
    except Exception as e:
        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Unexpected error: {e}", level=xbmc.LOGERROR)
        return None
