# Release info

Version: 1.5.2

Release date: October 17, 2022

# Important
1. Added required `port` config variable for camera API section. Defaults to `80` in the `config-template.json` template. Just add it to your existing config and you're good.

```json
  ...
  "camera_list": {
    "cam_1": {
      "api": {
        "host": "http://192.168.1.1",
        "port": 80,
        ...
```

# New features
N/A

# Misc
N/A
