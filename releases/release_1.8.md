# Release info

Version: 1.8

Release date: May 6, 2023

# Important

1. Add a new config variable `nvr` to `config.json` for each of your cameras.
2. This update can break things. Open a new issue if you find something.

# New features

1. Added new config variable `nvr` for your camera. Check `config-template.json`. It's
   for a case when your camera(s) is behind the NVR host so detecting alert (alarm)
   event types requires the available NVR channel name for the camera since the NVR
   Alert Stream will produce events for all cameras, and it needs to be properly parsed.

   ```json
   "nvr": {
     "is_behind": false,
     "channel_name": ""
   }
   ```

# Misc

N/A
