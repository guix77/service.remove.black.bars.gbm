# Aspect Ratio Detection Methods

This document describes the aspect ratio detection methods used by the addon.

## Primary Method: VideoPlayer.VideoAspect

**Status**: ✅ Primary method (fastest, most reliable)

**Implementation**: Uses Kodi's `VideoPlayer.VideoAspect` InfoLabel

**Advantages**:
- Fast (no network or JSON-RPC overhead)
- Works for most video sources
- Standard Kodi API

**Limitations**:
- May return the aspect ratio of the video file (including hardcoded black bars for some sources)
- Not always available for all video sources

**Code location**: `KodiMetadataProvider.get_aspect_ratio()` (primary method)

## Fallback Method: JSON-RPC Player.GetItem

**Status**: ✅ Fallback method (used when VideoPlayer.VideoAspect fails)

**Implementation**: Uses Kodi's JSON-RPC API with `Player.GetItem` method

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "Player.GetItem",
  "params": {
    "playerid": 1,
    "properties": ["streamdetails"]
  },
  "id": 1
}
```

**Response structure**:
```json
{
  "id": 1,
  "jsonrpc": "2.0",
  "result": {
    "item": {
      "streamdetails": {
        "video": [
          {
            "aspect": 2.4000000953674316,
            "codec": "hevc",
            "height": 1080,
            "width": 1920
          }
        ]
      }
    }
  }
}
```

**Advantages**:
- Works for Jellyfin/streaming sources when VideoPlayer.VideoAspect is unavailable
- Provides detailed stream information
- More reliable for some addon-based video sources

**Limitations**:
- Slower than InfoLabel (JSON-RPC overhead)
- May return the aspect ratio of the video file (including hardcoded black bars)

**Code location**: `KodiMetadataProvider.get_aspect_ratio()` (fallback method)

## Why Both Methods?

- **VideoPlayer.VideoAspect**: Fast and reliable for most cases
- **JSON-RPC Player.GetItem**: Fallback for cases where VideoPlayer.VideoAspect doesn't work (e.g., some Jellyfin/streaming scenarios)

Both methods return the aspect ratio of the video file as it is stored, which may include hardcoded black bars. For the original content aspect ratio (without black bars), use IMDb detection (when enabled).

