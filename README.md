# Remove Black Bars (GBM)

Kodi addon that automatically removes black bars by applying zoom. Uses IMDb for aspect ratio detection with local metadata fallback. Designed for GBM platforms (Linux/LibreELEC/CoreELEC/OSMC) without frame capture.

## Installation

1. Download the ZIP from releases
2. Kodi → Settings → Add-ons → Install from zip file

## Settings

**General**
- **Enable IMDb** (default: on): fetch aspect ratio from IMDb, requires internet
- **Enable IMDb cache** (default: on): cache results locally to reduce requests
- **Zoom narrow ratios** (default: off): also zoom 4:3 and other narrow ratios
- **Skip zoom for Catch-up TV** (default: on): skip zoom for CatchupTV and More content
- **Clear IMDb cache**: button to clear cached ratios

**Advanced**
- **16:9 tolerance min/max** (default: 175/180): ratio range considered as 16:9 — no zoom applied within this range
- **Notification duration** (default: 2000ms): duration of zoom notification

## How it works

### Aspect ratio detection

1. **IMDb** (primary): queries IMDb GraphQL API using the IMDb ID from Kodi metadata, falls back to title search if no ID available
2. **Kodi metadata** (fallback): calculates ratio from video stream resolution via JSON-RPC

### Encoded black bars

When an IMDb ratio is found, the addon compares it with the actual file ratio (from stream resolution). If they differ significantly (>5%), encoded black bars are detected and the zoom accounts for both encoded bars and display bars.

### Zoom calculation

- Wide content (>16:9): `zoom = imdb_ratio / 177`
- Encoded bars: `zoom = file_ratio / 177` or combined formula
- No zoom if file ratio is within 16:9 tolerance (175–180 by default)

### Examples

| Case | IMDb ratio | File ratio | Zoom |
|---|---|---|---|
| Standard 2.35:1 movie | 235 | 235 | 235/177 = 1.33x |
| Encoded bars | 185 | 166 | 185/166 = 1.11x |
| 16:9 file, wide content | 185 | 177 | 1.07x (geometric mean) |

## Manual toggle

```
RunAddon(service.remove.black.bars.gbm,toggle)
```

## Troubleshooting

- **No zoom**: check fullscreen mode, check Kodi debug logs for `service.remove.black.bars.gbm:`
- **Wrong zoom**: clear IMDb cache, verify ratio on IMDb matches your file
- **IMDb not working**: check internet connection, check logs for `[IMDb]` errors

## Credits

Inspired by [script.black.bars.never](https://github.com/osumoclement/script.black.bars.never)
