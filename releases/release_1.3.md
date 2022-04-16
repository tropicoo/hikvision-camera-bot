# Release info

Version: 1.3

Release date: April 15, 2022

# Important
1. Config file templates moved to `configs` directory.
2. Bot needs full re-configuration due to changed config templates with new items.
   Backup your config files and perform clean setup.

# New features
1. DVR file recordings and uploads to the Telegram group (file limit 2GB).
2. SRS re-stream server to decrease bandwidth and CPU load on the camera. Not mandatory, 
but when turned on (as in the default template), make sure that SRS, DVR and Video Gif "channels" are the same (101 or 102).
3. Telegram Livestream (direct stream won't work due to unsupported color profile).
   Telegram bug [#15684](https://bugs.telegram.org/c/15684).
4. New command `ir_on|off|auto_cam_*` to turn on/off infrared light.
5. Cameras can be hidden (ignored/skipped) from setup by setting `hidden` to `true` in `config.json`. Can be useful if camera doesn't work, but you don't want to delete the whole config section.
6. Hide unwanted command sections in camera `command_sections_visibility` config section.

# Misc
1. Migrated from `aiogram` to `pyrogram`.
2. New docker container (service) `hikvision-srs-server`.
