# Release info

Version: 2.0

Release date: February 17, 2025

# Important

Added Timelapse camera config section. This is a breaking change. 
If you have a previous configuration file, you need to update it.

Check updated template in the `config_template.json` file.


# New features

### Timelapse camera feature.
Each camera can be configured to take a picture at a specific interval, 
save the image to a specific folder and create a timelapse video.

Camera supports multiple timelapse configurations if needed.

```json
{
  "timelapse": [
    {
      "enabled": true,                            # Enable timelapse feature (true/false)
      "name": "Kitchen view",                     # Timelapse name
      "start_hour": 7,                            # Start hour (24h format)
      "end_hour": 18,                             # End hour (24h format)
      "snapshot_period": 10,                      # Camera snapshot period in seconds
      "video_length": 120,                        # Final timelapse video length in seconds
      "video_framerate": 30,                      # Timelapse video framerate
      "channel": 102,                             # Camera channel to take snapshots from
      "timezone": "Europe/Kyiv",                  # Server timezone
      "tmp_storage": "/data/timelapses",          # Temporary storage for snapshots
      "storage": "/data/timelapses",              # Final storage for timelapse video and optionally for snapshots
      "keep_stills": true,                        # Keep snapshots after timelapse video creation (true/false)
      "ffmpeg_log_level": "error",                # FFMPEG log level
      "image_quality": 30,                        # FFMPEG video codec image quality (-crf)
      "video_codec": "libx264",                   # FFMPEG video codec (libx264, libx265, vp9)
      "pix_fmt": "yuv420p",                       # FFMPEG pixel format (yuv420p, yuv422p, yuv444p)
      "custom_ffmpeg_args": "-preset ultrafast",  # Custom FFMPEG arguments
      "nice_value": 19,                           # FFMPEG process nice value (integer or null to disable
      "threads": 1                                # FFMPEG process threads (integer or null to disable)
    }
  ]
}
```

# Misc

Use `pydantic-settings` for `.env` file validation.
