import requests
import time
from bs4 import BeautifulSoup

import xbmc
import xbmcaddon
import xbmcgui

def notify(msg):
    """
    Show notification with configurable duration from settings.
    
    Args:
        msg: Message to display
    """
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


def _parse_aspect_ratio(aspect_ratio_text):
    """
    Parse aspect ratio text from IMDb and return as integer (e.g., 178 for 16:9).
    Handles formats like "16:9", "16:9 HD", "1.85 : 1", "2.35", etc.
    Returns None if parsing fails.
    """
    if not aspect_ratio_text:
        return None
    
    try:
        # Clean the text (remove HTML entities, extra spaces, etc.)
        text = aspect_ratio_text.strip()
        # Remove common suffixes like "HD", "SD", etc. (take first part)
        text = text.split()[0] if text.split() else text
        
        if ':' in text:
            # Format "16:9" or "1.85:1"
            parts = text.split(':')
            if len(parts) == 2:
                try:
                    num = float(parts[0].strip())
                    den = float(parts[1].strip())
                    if den > 0:
                        ratio = num / den
                        return int((ratio + 0.005) * 100)
                except (ValueError, ZeroDivisionError):
                    return None
        else:
            # Format "1.85" or "2.35"
            try:
                ratio = float(text)
                return int((ratio + 0.005) * 100)
            except ValueError:
                return None
    except Exception:
        return None
    return None


def _fetch_with_retry(url, headers, max_retries=2, timeout=10):
    """
    Fait une requête HTTP avec retry et exponential backoff.
    Retourne (response, error) où response est None en cas d'erreur.
    """
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response, None
        except requests.RequestException as e:
            if attempt < max_retries:
                # Exponential backoff: 100ms * 2^attempt
                delay_ms = 100 * (2 ** attempt)
                time.sleep(delay_ms / 1000.0)
                xbmc.log(f"service.remove.black.bars.gbm: Retry {attempt + 1}/{max_retries} for {url}", level=xbmc.LOGDEBUG)
                continue
            return None, e
    return None, None

def getOriginalAspectRatio(title, imdb_number=None):
    """
    Récupère le ratio d'aspect original depuis IMDb.
    Retourne None en cas d'erreur pour éviter les fuites mémoire.
    Toutes les exceptions sont gérées et les objets sont nettoyés.
    """
    search_page = None
    title_page = None
    tech_specs_page = None
    soup = None
    
    try:
        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Starting getOriginalAspectRatio with title='{title}', imdb_number='{imdb_number}'", level=xbmc.LOGDEBUG)
        
        BASE_URL = "https://www.imdb.com"
        HEADERS = {
            'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}

        if imdb_number:
            # Normalize for URL: add "tt" prefix if needed
            imdb_str = str(imdb_number)
            if imdb_str.isdigit():
                imdb_id = "tt" + imdb_str
            elif not imdb_str.startswith("tt"):
                imdb_id = "tt" + imdb_str
            else:
                imdb_id = imdb_str
            URL = "{}/title/{}/".format(BASE_URL, imdb_id)
            xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Using IMDb number directly, URL: {URL}", level=xbmc.LOGDEBUG)
        else:
            if not title:
                xbmc.log("service.remove.black.bars.gbm: [IMDb] No title provided for IMDb search", level=xbmc.LOGWARNING)
                return None
                
            URL = BASE_URL + "/find/?q={}".format(title)
            xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Searching IMDb with URL: {URL}", level=xbmc.LOGDEBUG)
            search_page, error = _fetch_with_retry(URL, HEADERS)
            if error:
                xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Error fetching IMDb search page: {error}", level=xbmc.LOGWARNING)
                return None

            xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Search page fetched successfully, length: {len(search_page.text)}", level=xbmc.LOGDEBUG)
            
            # lxml parser would have been better but not currently supported in Kodi
            soup = BeautifulSoup(search_page.text, 'html.parser')

            # Try multiple strategies to find the title link
            title_url = None
            
            # Strategy 1: Find the title element and look for link in the same list item
            title_url_tag = soup.select_one('.ipc-metadata-list-summary-item__t')
            if title_url_tag:
                xbmc.log("service.remove.black.bars.gbm: [IMDb] Found title element with selector '.ipc-metadata-list-summary-item__t'", level=xbmc.LOGDEBUG)
                # Find the parent <li> element
                list_item = title_url_tag
                for _ in range(5):  # Go up to 5 levels to find the <li>
                    if list_item and list_item.name == 'li':
                        break
                    list_item = list_item.parent if list_item else None
                
                if list_item:
                    # Look for the link with class 'ipc-title-link-wrapper' in the same <li>
                    link_tag = list_item.find('a', class_='ipc-title-link-wrapper', href=True)
                    if link_tag:
                        title_url = link_tag.get('href')
                        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Found href in ipc-title-link-wrapper: {title_url}", level=xbmc.LOGDEBUG)
                    else:
                        # Fallback: look for any /title/ link in the same <li>
                        link_tag = list_item.find('a', href=lambda x: x and '/title/tt' in x)
                        if link_tag:
                            title_url = link_tag.get('href')
                            xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Found /title/ link in list item: {title_url}", level=xbmc.LOGDEBUG)
            
            # Strategy 2: Try to find link with title pattern directly in search results
            if not title_url:
                xbmc.log("service.remove.black.bars.gbm: [IMDb] Trying alternative strategy: searching for /title/ links", level=xbmc.LOGDEBUG)
                # Find all links that contain /title/tt
                all_links = soup.find_all('a', href=lambda x: x and '/title/tt' in x)
                for link in all_links:
                    href = link.get('href', '')
                    # Check if it's in a result item (not navigation)
                    parent = link.parent
                    for _ in range(5):  # Check up to 5 levels up
                        if parent:
                            if hasattr(parent, 'get'):
                                classes = parent.get('class', [])
                                if classes:
                                    # Check if it's in a search result item
                                    if any('ipc-metadata-list-summary-item' in str(c) for c in classes) or \
                                       any('find-result' in str(c) for c in classes):
                                        title_url = href
                                        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Found /title/ link in search results: {title_url}", level=xbmc.LOGDEBUG)
                                        break
                            if title_url:
                                break
                            parent = parent.parent
                        else:
                            break
                    if title_url:
                        break
            
            if title_url:
                # Extract IMDb number from URL (handles both /title/ and /fr/title/ formats)
                # URL format: /fr/title/tt9737326/?ref_=fn_t_1 or /title/tt9737326/
                imdb_number = None
                if '/title/' in title_url:
                    imdb_number = title_url.rsplit('/title/', 1)[-1].split("/")[0].split("?")[0]
                elif '/title/' in title_url.replace('/fr/', '/').replace('/en/', '/'):
                    # Handle language prefix
                    imdb_number = title_url.rsplit('/title/', 1)[-1].split("/")[0].split("?")[0]
                
                if imdb_number:
                    xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Extracted IMDb number from URL: {imdb_number}", level=xbmc.LOGDEBUG)
                    # Normalize URL: remove language prefix and query params, ensure it starts with /
                    # Convert /fr/title/tt9737326/?ref_=fn_t_1 to /title/tt9737326/
                    normalized_url = title_url
                    # Remove language prefix if present
                    if '/fr/title/' in normalized_url or '/en/title/' in normalized_url:
                        normalized_url = normalized_url.replace('/fr/title/', '/title/').replace('/en/title/', '/title/')
                    # Remove query params
                    if '?' in normalized_url:
                        normalized_url = normalized_url.split('?')[0]
                    # Ensure it starts with /
                    if not normalized_url.startswith('/'):
                        normalized_url = '/' + normalized_url
                    # Ensure it ends with /
                    if not normalized_url.endswith('/'):
                        normalized_url = normalized_url + '/'
                    URL = BASE_URL + normalized_url
                else:
                    xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Failed to extract IMDb number from URL: {title_url}", level=xbmc.LOGWARNING)
                    soup = None
                    return None
            else:
                xbmc.log("service.remove.black.bars.gbm: [IMDb] No link found in IMDb search results", level=xbmc.LOGWARNING)
                # Log page preview for debugging (only first 500 chars to avoid memory issues)
                page_preview = search_page.text[:500] if len(search_page.text) > 500 else search_page.text
                xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Page preview: {page_preview}", level=xbmc.LOGDEBUG)
                # Clean up before returning
                soup = None
                return None
            
            # Clean up search page soup after use
            soup = None

        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Fetching title page: {URL}", level=xbmc.LOGDEBUG)
        title_page, error = _fetch_with_retry(URL, HEADERS)
        if error:
            xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Error fetching IMDb title page: {error}", level=xbmc.LOGWARNING)
            return None
        
        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Title page fetched successfully, length: {len(title_page.text)}", level=xbmc.LOGDEBUG)
        soup = BeautifulSoup(title_page.text, 'html.parser')

        # this below could have worked instead but for some reason SoupSieve not working inside Kodi
        aspect_ratio_tags = soup.find(attrs={"data-testid": "title-techspec_aspectratio"})
        
        aspect_ratio = None
        
        if aspect_ratio_tags:
            xbmc.log("service.remove.black.bars.gbm: [IMDb] Found aspect ratio tags with data-testid", level=xbmc.LOGDEBUG)
            aspect_ratio_item = aspect_ratio_tags.select_one(".ipc-metadata-list-item__list-content-item")
            
            if aspect_ratio_item:
                aspect_ratio_full = aspect_ratio_item.decode_contents()
                xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Aspect ratio full text: {aspect_ratio_full}", level=xbmc.LOGDEBUG)

                if aspect_ratio_full:
                    aspect_ratio_int = _parse_aspect_ratio(aspect_ratio_full)
                    if aspect_ratio_int:
                        aspect_ratio = str(aspect_ratio_int)
                        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Extracted aspect ratio from '{aspect_ratio_full}': {aspect_ratio}", level=xbmc.LOGINFO)
                    else:
                        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Failed to parse aspect ratio from '{aspect_ratio_full}'", level=xbmc.LOGWARNING)
                        aspect_ratio = None
        else:
            xbmc.log("service.remove.black.bars.gbm: [IMDb] No aspect ratio tags found with data-testid, trying technical specs page", level=xbmc.LOGDEBUG)
        
        if not aspect_ratio and imdb_number:
            # check if video has multiple aspect ratios
            try:
                # Normalize for URL: add "tt" prefix if needed
                imdb_str = str(imdb_number)
                if imdb_str.isdigit():
                    imdb_id = "tt" + imdb_str
                elif not imdb_str.startswith("tt"):
                    imdb_id = "tt" + imdb_str
                else:
                    imdb_id = imdb_str
                URL = "{}/title/{}/technical/".format(BASE_URL, imdb_id)
                xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Fetching technical specs page: {URL}", level=xbmc.LOGDEBUG)
                tech_specs_page, error = _fetch_with_retry(URL, HEADERS)
                if error:
                    xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Error fetching technical specs page: {error}", level=xbmc.LOGWARNING)
                    # Clean up before returning
                    soup = None
                    return None
                
                xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Technical specs page fetched successfully", level=xbmc.LOGDEBUG)
                # Clean up previous soup before creating new one
                soup = None
                soup = BeautifulSoup(tech_specs_page.text, 'html.parser')
                aspect_ratio_container = soup.select_one("#aspectratio")
                
                if aspect_ratio_container:
                    xbmc.log("service.remove.black.bars.gbm: [IMDb] Found aspect ratio container", level=xbmc.LOGDEBUG)
                    aspect_ratio_li = aspect_ratio_container.find_all("li")
                    xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Found {len(aspect_ratio_li)} aspect ratio entries", level=xbmc.LOGDEBUG)
                    
                    if len(aspect_ratio_li) > 1:
                        aspect_ratios = []

                        for li in aspect_ratio_li:
                            aspect_ratio_item = li.select_one(".ipc-metadata-list-item__list-content-item")
                            
                            if not aspect_ratio_item:
                                continue
                                
                            aspect_ratio_full = aspect_ratio_item.decode_contents()
                            
                            if not aspect_ratio_full:
                                continue
                            
                            aspect_ratio_int = _parse_aspect_ratio(aspect_ratio_full)
                            if not aspect_ratio_int:
                                continue
                            
                            aspect_ratio = str(aspect_ratio_int)
                            
                            sub_text_item = li.select_one(".ipc-metadata-list-item__list-content-item--subText")
                            if sub_text_item:
                                sub_text = sub_text_item.decode_contents()
                                xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Found aspect ratio {aspect_ratio} with subtext: {sub_text}", level=xbmc.LOGDEBUG)
                                
                                if sub_text == "(theatrical ratio)":
                                    xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Using theatrical ratio: {aspect_ratio}", level=xbmc.LOGINFO)
                                    # Clean up before returning
                                    soup = None
                                    return aspect_ratio
                            
                            aspect_ratios.append(aspect_ratio)

                        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Multiple aspect ratios found: {aspect_ratios}", level=xbmc.LOGDEBUG)
                        # Clean up before returning
                        soup = None
                        return aspect_ratios
                    else:
                        xbmc.log("service.remove.black.bars.gbm: [IMDb] Only one aspect ratio entry found, skipping multiple ratio logic", level=xbmc.LOGDEBUG)
                else:
                    xbmc.log("service.remove.black.bars.gbm: [IMDb] No aspect ratio container found in technical specs", level=xbmc.LOGDEBUG)
            except requests.RequestException as e:
                xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Error fetching technical specs page: {e}", level=xbmc.LOGWARNING)
                soup = None
            except Exception as e:
                xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Error parsing technical specs: {e}", level=xbmc.LOGWARNING)
                soup = None

        # Clean up soup before returning
        soup = None
        
        if aspect_ratio:
            xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Returning aspect ratio: {aspect_ratio}", level=xbmc.LOGINFO)
        else:
            xbmc.log("service.remove.black.bars.gbm: [IMDb] No aspect ratio found", level=xbmc.LOGWARNING)
        return aspect_ratio
    except Exception as e:
        # Catch-all pour éviter les fuites mémoire dues aux exceptions non gérées
        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Unexpected error in getOriginalAspectRatio: {e}", level=xbmc.LOGERROR)
        import traceback
        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Traceback: {traceback.format_exc()}", level=xbmc.LOGERROR)
        # Clean up all objects in case of exception
        soup = None
        return None
    finally:
        # Explicit cleanup to help garbage collection
        # Note: requests automatically closes connections, but we clear references
        search_page = None
        title_page = None
        tech_specs_page = None
        soup = None