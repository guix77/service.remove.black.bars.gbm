# CLAUDE.md

## Tests

```
uv run --with pytest --with requests pytest tests/ -v
```

## Python tooling

Use `uv` — never create a `.venv` or use `pip install` directly.

## Project structure

- `addon.py` — Kodi service (detection, zoom, cache, settings)
- `imdb.py` — IMDb aspect ratio lookup
- `resources/settings.xml` — Kodi settings UI
- `tests/` — pytest suite with Kodi mocks (`tests/mock_kodi.py`)
- `CASES.jsonl` — real-world cases for manual validation and regression tests

## IMDb API

Uses two unofficial IMDb endpoints (no WAF, no BeautifulSoup):

- **GraphQL** `POST https://graphql.imdb.com/` — fetch aspect ratios by IMDb ID
- **Suggest** `GET https://sg.media-imdb.com/suggests/{first_char}/{query}.json` — JSONP, title → IMDb ID fallback

The HTML scraper was replaced in 2026 because IMDb deployed AWS WAF (permanent JS challenge on all HTML pages since ~March 2026).

## Kodi addon constraints

- The ZIP is built by a GitHub Action — no dev artifacts in the repo
- Dependencies declared in `addon.xml` (only `script.module.requests`)
- Tested on LibreELEC with Jellyfin as media backend
- IMDb ID comes from Kodi JSON-RPC `Player.GetItem` → `uniqueid.imdb` (provided by Jellyfin)
- For series/episodes, Jellyfin sometimes provides a TVDB ID instead of IMDb ID → title search fallback kicks in

## Adding a real-world test case

1. Play the video, copy the `CASES.jsonl entry` line from Kodi logs
2. Fill in `ideal_zoom` manually
3. Add the line to `CASES.jsonl`
4. `test_real_world_cases.py` picks it up automatically
