# Remove Black Bars (GBM)

A Kodi addon that automatically removes black bars by applying intelligent zoom using IMDb (enabled by default) with local metadata fallback. Designed for GBM platforms (Linux/LE/CE/OSMC) without frame capture.

## Requirements

- Kodi 19 (Matrix) or later
- Internet connection (optional, for IMDb detection)

## Features

- Automatically removes black bars during video playback
- Uses IMDb for aspect ratio detection (enabled by default, requires internet)
- Falls back to local Kodi metadata if IMDb is unavailable or ratio not found
- Detects and handles encoded black bars (when file aspect ratio differs from content)
- Local cache for improved performance
- Configurable 16:9 proximity tolerance
- Configurable notification duration
- Designed for GBM architecture without RenderCapture

## Installation

1. Download the addon ZIP file
2. In Kodi, go to Settings → Add-ons → Install from zip file
3. Select the downloaded ZIP file
4. The addon will start automatically when video playback begins

## Configuration

### General Settings

- **Enable IMDb**: Enable/disable IMDb aspect ratio detection (default: enabled)
  - When enabled, scrapes IMDb website to get accurate aspect ratios
  - Requires internet connection
  - Falls back to local metadata if unavailable

- **Enable IMDb cache**: Enable/disable caching of IMDb results (default: enabled)
  - Caches aspect ratios locally to reduce web requests
  - Cache location: Kodi addon profile directory

- **Zoom narrow ratios**: Enable zooming for narrow aspect ratios like 4:3 (default: disabled)
  - When disabled, only wide ratios (>16:9) are zoomed
  - When enabled, narrow ratios (<16:9) are also zoomed to fill screen

- **Clear IMDb cache**: Button to clear the cached aspect ratios

### Advanced Settings

- **16:9 proximity tolerance (min)**: Minimum ratio considered close to 16:9 (default: 175)
  - Files with aspect ratio between min and max are considered 16:9
  - No zoom is applied for these files

- **16:9 proximity tolerance (max)**: Maximum ratio considered close to 16:9 (default: 180)
  - Files with aspect ratio between min and max are considered 16:9
  - No zoom is applied for these files

- **Notification duration**: Duration of zoom notifications in milliseconds (default: 2000)
  - Range: 1000-5000 ms
  - Set to 0 to disable notifications (not recommended)

## Usage

The addon works automatically once installed and enabled:

1. Start playing a video in Kodi
2. The addon detects the aspect ratio (IMDb first, then local metadata)
3. If black bars are detected, zoom is automatically applied
4. A notification shows the applied zoom level (e.g., "Zoom 1.33x applied")
5. If no zoom is needed, a "No zoom needed" notification is shown

### Manual Control

You can toggle zoom on/off using the addon's context menu or by calling:
```
RunAddon(service.remove.black.bars.gbm,toggle)
```

## How It Works

### Aspect Ratio Detection

1. **IMDb Detection (Primary)**:
   - Scrapes IMDb website using video title, year, and IMDb ID
   - Gets the original aspect ratio of the content
   - Caches results locally for future use

2. **Local Metadata (Fallback)**:
   - Uses Kodi's `VideoPlayer.VideoAspect` InfoLabel
   - Only used if IMDb is disabled or unavailable

### Encoded Black Bars Detection

When IMDb ratio is available:
- Compares IMDb ratio (content) with file aspect ratio
- If difference > 5% (minimum 5), encoded black bars are detected
- Zoom is calculated to remove both encoded and display black bars

### Zoom Calculation

- **Wide ratios (>16:9)**: Zoom = detected_ratio / 177
- **Narrow ratios (<16:9)**: Zoom = 177 / detected_ratio (if enabled)
- **16:9 proximity**: No zoom if file ratio is within tolerance range (175-180)
- **Encoded black bars**: Zoom = file_ratio / detected_ratio

### Cache Management

- **Validation**: Invalid ratios (outside 100-500 range) are rejected

## Examples

### Example 1: Standard 2.35:1 Movie

- **IMDb ratio**: 235 (2.35:1)
- **File ratio**: 235 (no encoded black bars)
- **Zoom applied**: 235 / 177 = 1.33x
- **Result**: Black bars removed, content fills screen

### Example 2: Movie with Encoded Black Bars

- **IMDb ratio**: 235 (2.35:1 content)
- **File ratio**: 177 (16:9 file with encoded black bars)
- **Zoom applied**: 177 / 235 = 0.75x (no zoom, file is already 16:9)
- **Result**: No zoom needed, file already fits screen

### Example 3: 16:9 File with Wide Content

- **IMDb ratio**: 185 (1.85:1 content)
- **File ratio**: 177 (16:9 file)
- **Zoom applied**: 1.0x (no zoom, file is within 16:9 tolerance)
- **Result**: No zoom needed, file already fits screen

## Troubleshooting

### Zoom Not Applied

1. **Check if video is playing**: The addon only works during video playback
2. **Check if fullscreen**: Zoom is only applied in fullscreen mode (window ID 12005)
3. **Check logs**: Enable debug logging in Kodi settings to see detailed information
4. **Check aspect ratio**: Very unusual aspect ratios (<100 or >500) are rejected

### Incorrect Zoom

1. **Check IMDb data**: Verify the aspect ratio on IMDb matches your video
2. **Clear cache**: Try clearing the IMDb cache and let it re-detect
3. **Adjust tolerance**: Modify 16:9 proximity tolerance if needed
4. **Check for encoded black bars**: The addon should detect these automatically

### IMDb Not Working

1. **Check internet connection**: IMDb detection requires internet
2. **Check IMDb setting**: Verify "Enable IMDb" is enabled in addon settings
3. **Check video metadata**: Ensure video has title and year in Kodi library
4. **Check logs**: Look for IMDb scraping errors in Kodi logs
5. **IMDb website changes**: If IMDb changes their website structure, scraping may fail

### Cache Issues

1. **Clear cache**: Use the "Clear IMDb cache" button in settings
2. **Check disk space**: Ensure Kodi profile directory has write permissions

### Performance Issues

1. **Disable cache**: If cache is causing issues, disable it in settings
2. **Check rate limiting**: Zoom is rate-limited to once per 500ms

## Architecture

### Components

- **Service**: Main addon service that monitors video playback
- **ZoomApplier**: Handles zoom calculation and application
- **IMDbProvider**: Scrapes IMDb website for aspect ratios
- **KodiMetadataProvider**: Gets aspect ratios from Kodi metadata
- **JsonCacheProvider**: Manages local cache

### Data Flow

1. Video playback starts → `onAVStarted()` event
2. Extract video metadata (title, year, IMDb ID)
3. Check cache for aspect ratio
4. If not cached, scrape IMDb website
5. Get file aspect ratio from Kodi
6. Compare ratios to detect encoded black bars
7. Calculate zoom amount
8. Apply zoom via JSON-RPC `Player.SetViewMode`
9. Show notification

## Development

### Running Tests

```bash
python3 -m pytest tests/ -v
```

### Code Structure

- `addon.py`: Main addon code
- `imdb.py`: IMDb website scraping integration
- `tests/`: Unit tests
- `resources/settings.xml`: Addon settings definition

## Credits

Inspired from https://github.com/osumoclement/script.black.bars.never

## License

MIT - See [LICENSE](LICENSE) file for details.

