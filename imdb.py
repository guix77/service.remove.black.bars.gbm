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
    """
    try:
        BASE_URL = "https://www.imdb.com/"
        HEADERS = {
            'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}

        # Normalize IMDb number: add "tt" prefix if it's just a number
        if imdb_number:
            imdb_str = str(imdb_number)
            if imdb_str.isdigit():
                imdb_number = "tt" + imdb_str
            elif not imdb_str.startswith("tt"):
                imdb_number = "tt" + imdb_str
        
        if imdb_number and str(imdb_number).startswith("tt"):
            URL = "{}/title/{}/".format(BASE_URL, imdb_number)
        else:
            if not title:
                xbmc.log("service.remove.black.bars.gbm: No title provided for IMDb search", level=xbmc.LOGWARNING)
                return None
                
            URL = BASE_URL + "find/?q={}".format(title)
            search_page, error = _fetch_with_retry(URL, HEADERS)
            if error:
                xbmc.log("service.remove.black.bars.gbm: Error fetching IMDb search page: " + str(error), level=xbmc.LOGWARNING)
                return None

            # lxml parser would have been better but not currently supported in Kodi
            soup = BeautifulSoup(search_page.text, 'html.parser')

            # Try multiple selectors to find the title link
            title_url_tag = None
            title_url = None
            
            # Strategy 1: Try finding result container first
            result_container = soup.find('ul', class_='ipc-metadata-list') or soup.find('ul', class_='findList')
            if result_container:
                xbmc.log("service.remove.black.bars.gbm: Found result container", level=xbmc.LOGDEBUG)
                # Try to find first result link
                first_result = result_container.find('a', href=lambda h: h and '/title/tt' in h)
                if first_result:
                    title_url_tag = first_result
                    xbmc.log("service.remove.black.bars.gbm: Found first result link in container", level=xbmc.LOGDEBUG)
            
            # Strategy 2: Direct link selector
            if not title_url_tag:
                title_url_tag = soup.select_one('.ipc-metadata-list-summary-item__t a')
                if title_url_tag:
                    xbmc.log("service.remove.black.bars.gbm: Found link with selector '.ipc-metadata-list-summary-item__t a'", level=xbmc.LOGDEBUG)
            
            # Strategy 3: Find title element then link inside
            if not title_url_tag:
                title_element = soup.select_one('.ipc-metadata-list-summary-item__t')
                if title_element:
                    xbmc.log("service.remove.black.bars.gbm: Found title element, looking for link inside", level=xbmc.LOGDEBUG)
                    # Try parent link
                    parent = title_element.parent
                    if parent and parent.name == 'a':
                        title_url_tag = parent
                        xbmc.log("service.remove.black.bars.gbm: Found link in parent of title element", level=xbmc.LOGDEBUG)
                    else:
                        # Try finding any link in the element or nearby
                        title_url_tag = title_element.find('a', href=True)
                        if not title_url_tag:
                            # Try next sibling
                            next_sibling = title_element.find_next_sibling('a', href=True)
                            if next_sibling:
                                title_url_tag = next_sibling
                                xbmc.log("service.remove.black.bars.gbm: Found link in next sibling", level=xbmc.LOGDEBUG)
            
            # Strategy 4: Try alternative selectors - find any link with /title/tt
            if not title_url_tag:
                xbmc.log("service.remove.black.bars.gbm: Trying alternative selectors", level=xbmc.LOGDEBUG)
                # Try finding any link with /title/ in href (prioritize first result)
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    if '/title/tt' in href:
                        title_url_tag = link
                        xbmc.log(f"service.remove.black.bars.gbm: Found link with /title/tt: {href[:100]}", level=xbmc.LOGDEBUG)
                        break
            
            if title_url_tag:
                # Log what we found
                tag_name = title_url_tag.name if hasattr(title_url_tag, 'name') else 'unknown'
                tag_attrs = str(title_url_tag.attrs)[:200] if hasattr(title_url_tag, 'attrs') else 'no attrs'
                xbmc.log(f"service.remove.black.bars.gbm: Found element: {tag_name}, attrs: {tag_attrs}", level=xbmc.LOGDEBUG)
                
                # Try to get href
                title_url = title_url_tag.get('href')
                if not title_url:
                    # Log all attributes for debugging
                    all_attrs = title_url_tag.attrs if hasattr(title_url_tag, 'attrs') else {}
                    xbmc.log(f"service.remove.black.bars.gbm: No 'href' attribute. All attrs: {all_attrs}", level=xbmc.LOGWARNING)
                    # Try to get href from parent or child
                    if hasattr(title_url_tag, 'parent') and title_url_tag.parent:
                        parent_href = title_url_tag.parent.get('href') if hasattr(title_url_tag.parent, 'get') else None
                        if parent_href:
                            title_url = parent_href
                            xbmc.log(f"service.remove.black.bars.gbm: Found href in parent: {title_url}", level=xbmc.LOGDEBUG)
                    # Try finding href in children
                    if not title_url and hasattr(title_url_tag, 'find'):
                        child_link = title_url_tag.find('a', href=True)
                        if child_link:
                            title_url = child_link.get('href')
                            xbmc.log(f"service.remove.black.bars.gbm: Found href in child: {title_url}", level=xbmc.LOGDEBUG)
                
                if title_url:
                    # Ensure it's a full URL or relative path
                    if not title_url.startswith('http'):
                        if not title_url.startswith('/'):
                            title_url = '/' + title_url
                    imdb_number = title_url.rsplit('/title/', 1)[-1].split("/")[0]
                    xbmc.log(f"service.remove.black.bars.gbm: Extracted IMDb number: {imdb_number}", level=xbmc.LOGDEBUG)
                    URL = BASE_URL + title_url.lstrip('/')
                else:
                    xbmc.log("service.remove.black.bars.gbm: No 'href' attribute found in title_url_tag after all attempts", level=xbmc.LOGWARNING)
                    return None
            else:
                # Log what we found in the page for debugging
                xbmc.log("service.remove.black.bars.gbm: No title found in IMDb search results", level=xbmc.LOGWARNING)
                # Try to find any clues in the HTML
                page_preview = search_page.text[:500] if len(search_page.text) > 500 else search_page.text
                xbmc.log(f"service.remove.black.bars.gbm: Page preview: {page_preview}", level=xbmc.LOGDEBUG)
                return None

        title_page, error = _fetch_with_retry(URL, HEADERS)
        if error:
            xbmc.log("service.remove.black.bars.gbm: Error fetching IMDb title page: " + str(error), level=xbmc.LOGWARNING)
            return None
            
        soup = BeautifulSoup(title_page.text, 'html.parser')

        # this below could have worked instead but for some reason SoupSieve not working inside Kodi
        aspect_ratio_tags = soup.find(
            attrs={"data-testid": "title-techspec_aspectratio"})
        
        aspect_ratio = None
        
        if aspect_ratio_tags:
            aspect_ratio_item = aspect_ratio_tags.select_one(
                ".ipc-metadata-list-item__list-content-item")
            
            if aspect_ratio_item:
                aspect_ratio_full = aspect_ratio_item.decode_contents()

                """aspect_ratio_full = soup.find(
                    attrs={"data-testid": "title-techspec_aspectratio"}).css.select(".ipc-metadata-list-item__list-content-item")[0].decode_contents()
                    """

                if aspect_ratio_full:
                    aspect_ratio = aspect_ratio_full.split(':')[0].replace('.', '')
        
        if not aspect_ratio and imdb_number:
            # check if video has multiple aspect ratios
            try:
                URL = "{}/title/{}/technical/".format(BASE_URL, imdb_number)
                tech_specs_page, error = _fetch_with_retry(URL, HEADERS)
                if error:
                    raise error
                soup = BeautifulSoup(tech_specs_page.text, 'html.parser')
                aspect_ratio_container = soup.select_one("#aspectratio")
                
                if aspect_ratio_container:
                    aspect_ratio_li = aspect_ratio_container.find_all("li")
                    if len(aspect_ratio_li) > 1:
                        aspect_ratios = []

                        for li in aspect_ratio_li:
                            aspect_ratio_item = li.select_one(
                                ".ipc-metadata-list-item__list-content-item")
                            
                            if not aspect_ratio_item:
                                continue
                                
                            aspect_ratio_full = aspect_ratio_item.decode_contents()
                            
                            if not aspect_ratio_full:
                                continue
                            
                            aspect_ratio = aspect_ratio_full.split(':')[0].replace('.', '')
                            
                            sub_text_item = li.select_one(".ipc-metadata-list-item__list-content-item--subText")
                            if sub_text_item:
                                sub_text = sub_text_item.decode_contents()
                                
                                if sub_text == "(theatrical ratio)":
                                    xbmc.log("service.remove.black.bars.gbm: using theatrical ratio " + str(aspect_ratio), level=xbmc.LOGINFO)
                                    return aspect_ratio
                            
                            aspect_ratios.append(aspect_ratio)

                        return aspect_ratios
            except requests.RequestException as e:
                xbmc.log("service.remove.black.bars.gbm: Error fetching technical specs page: " + str(e), level=xbmc.LOGWARNING)
            except Exception as e:
                xbmc.log("service.remove.black.bars.gbm: Error parsing technical specs: " + str(e), level=xbmc.LOGWARNING)

        return aspect_ratio
    except Exception as e:
        # Catch-all pour éviter les fuites mémoire dues aux exceptions non gérées
        xbmc.log("service.remove.black.bars.gbm: Unexpected error in getOriginalAspectRatio: " + str(e), level=xbmc.LOGERROR)
        return None