import requests
import time
from bs4 import BeautifulSoup

import xbmc
import xbmcgui

def notify(msg):
    xbmcgui.Dialog().notification("Remove Black Bars (GBM)", msg, None, 1000)


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

        # Normalize IMDb number: add "tt" prefix if it's just a number
        if imdb_number:
            imdb_str = str(imdb_number)
            if imdb_str.isdigit():
                imdb_number = "tt" + imdb_str
                xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Normalized IMDb number to: {imdb_number}", level=xbmc.LOGDEBUG)
            elif not imdb_str.startswith("tt"):
                imdb_number = "tt" + imdb_str
                xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Added 'tt' prefix to IMDb number: {imdb_number}", level=xbmc.LOGDEBUG)
        
        if imdb_number and str(imdb_number).startswith("tt"):
            URL = "{}/title/{}/".format(BASE_URL, imdb_number)
            xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Using IMDb number directly, URL: {URL}", level=xbmc.LOGDEBUG)
        else:
            if not title:
                xbmc.log("service.remove.black.bars.gbm: [IMDb] No title provided for IMDb search", level=xbmc.LOGWARNING)
                return None
                
            URL = BASE_URL + "find/?q={}".format(title)
            xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Searching IMDb with URL: {URL}", level=xbmc.LOGDEBUG)
            search_page, error = _fetch_with_retry(URL, HEADERS)
            if error:
                xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Error fetching IMDb search page: {error}", level=xbmc.LOGWARNING)
                return None

            xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Search page fetched successfully, length: {len(search_page.text)}", level=xbmc.LOGDEBUG)
            
            # lxml parser would have been better but not currently supported in Kodi
            soup = BeautifulSoup(search_page.text, 'html.parser')

            # Use simple selector like old code
            title_url_tag = soup.select_one('.ipc-metadata-list-summary-item__t')
            if title_url_tag:
                xbmc.log("service.remove.black.bars.gbm: [IMDb] Found title element with selector '.ipc-metadata-list-summary-item__t'", level=xbmc.LOGDEBUG)
                try:
                    # Try to get href directly like old code
                    title_url = title_url_tag['href']
                    xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Found href in title element: {title_url}", level=xbmc.LOGDEBUG)
                except (KeyError, TypeError):
                    # Fallback: try to find link inside
                    xbmc.log("service.remove.black.bars.gbm: [IMDb] No 'href' in title element, looking for link inside", level=xbmc.LOGDEBUG)
                    link_tag = title_url_tag.find('a', href=True)
                    if link_tag:
                        title_url = link_tag.get('href')
                        xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Found href in link inside: {title_url}", level=xbmc.LOGDEBUG)
                    else:
                        xbmc.log("service.remove.black.bars.gbm: [IMDb] No link found in title element", level=xbmc.LOGWARNING)
                        # Clean up before returning
                        soup = None
                        return None
                
                imdb_number = title_url.rsplit('/title/', 1)[-1].split("/")[0]
                xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Extracted IMDb number from URL: {imdb_number}", level=xbmc.LOGDEBUG)
                # Ensure title_url starts with / and combine with BASE_URL
                if not title_url.startswith('/'):
                    title_url = '/' + title_url
                URL = BASE_URL + title_url
            else:
                xbmc.log("service.remove.black.bars.gbm: [IMDb] No title found in IMDb search results with selector '.ipc-metadata-list-summary-item__t'", level=xbmc.LOGWARNING)
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
                    aspect_ratio = aspect_ratio_full.split(':')[0].replace('.', '')
                    xbmc.log(f"service.remove.black.bars.gbm: [IMDb] Extracted aspect ratio: {aspect_ratio}", level=xbmc.LOGINFO)
        else:
            xbmc.log("service.remove.black.bars.gbm: [IMDb] No aspect ratio tags found with data-testid, trying technical specs page", level=xbmc.LOGDEBUG)
        
        if not aspect_ratio and imdb_number:
            # check if video has multiple aspect ratios
            try:
                URL = "{}/title/{}/technical/".format(BASE_URL, imdb_number)
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
                            
                            aspect_ratio = aspect_ratio_full.split(':')[0].replace('.', '')
                            
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