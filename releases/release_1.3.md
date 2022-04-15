# Release info

Version: 1.3

Release date: April 15, 2022

# Important
1. Config file templates moved to `configs` directory.
2. Bot needs full re-configuration due to changed config templates with new items.
   Backup your config files and perform clean set up.

# New features
1. DVR file recordings and uploads to the Telegram group (file limit 2GB).
2. SRS re-stream server to decrease bandwidth and CPU load on the camera. Not mandatory.
3. Telegram stream (direct stream won't work due to unsupported color profile).
   Telegram bug [#15684](https://bugs.telegram.org/c/15684).
4. New command `ir_on|off|auto_cam_*` to turn on/off infrared light.

# Misc
1. Migrated from `aiogram` to `pyrogram`.
2. New docker container (service) `hikvision-srs-server`.
3. Cameras can be hidden (ignored/skipped) from setup by setting `hidden` to `true` in `config.json`. Can be useful if camera doesn't work but you don't want to delete the whole config section.
