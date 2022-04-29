# Release info

Version: 1.4

Release date:

# Important
1. Bot needs full re-configuration (again) due to changed config templates with new items.
   Backup your config files and perform clean setup.

# New features
1. Introduced three new config variables `chat_users`, `alert_users` and 
`startup_message_users` to replace `allowed_user_ids` for more granular access setup:
   * `chat_users` - user/group IDs which can interact with bot. Cannot be empty.
   * `alert_users` - user/channel/group IDs where alerts will be sent if turned on. Cannot be empty.
   * `startup_message_users` - user/channel/group IDs where startup message is sent. Can be empty to remain silent.
2. Introduced new per camera config variable `group` and command `/groups` to group cameras.
3. Added new commands `/version`, `/ver`, `/v` to check the latest bot version.
   


# Misc
1. Bumped Python version from 3.9 to 3.10 in Dockerfile.
2. If text message from the bot exceeds max size it will be split and sent with smaller chunks.
3. SRS re-stream is now disabled by default in the config template.
