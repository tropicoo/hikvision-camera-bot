# Release info

Version: 1.6

Release date: October 18, 2022

# Important
1. Full reconfiguration is required (or manual editing your current `config.json` config file)

# New features
1. Added new boolean config variable `send_text` to control sending alert text message for every type of detection
```json
...
      "alert": {
        "motion_detection": {
          ...
          "send_text": true
        },
        "line_crossing_detection": {
          ...
          "send_text": true
        },
        "intrusion_detection": {
          ...
          "send_text": true
        }
      },
...
```
2. Added new config section `picture` to control which channel use for taking pictures. Useful when several cameras are accessible through on IP address or host. 
```json
...
      "picture": {
        "on_demand": {
          "channel": 101
        },
        "on_alert": {
          "channel": 101
        }
      },
...
```

# Misc
N/A
