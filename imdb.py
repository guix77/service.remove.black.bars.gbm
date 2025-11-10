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

            title_url_tag = soup.select_one(
                '.ipc-metadata-list-summary-item__t')
            if title_url_tag:
                # we have matches, pick the first one
                # Use .get() to safely access 'href' attribute
                title_url = title_url_tag.get('href')
                if not title_url:
                    xbmc.log("service.remove.black.bars.gbm: No 'href' attribute found in title_url_tag", level=xbmc.LOGWARNING)
                    return None
                imdb_number = title_url.rsplit(
                    '/title/', 1)[-1].split("/")[0]
                # this below could have worked instead but for some reason SoupSieve not working inside Kodi
                """title_url = soup.css.select(
                    '.ipc-metadata-list-summary-item__t')[0].get('href')
                    """

                URL = BASE_URL + title_url
            else:
                xbmc.log("service.remove.black.bars.gbm: No title found in IMDb search results", level=xbmc.LOGWARNING)
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