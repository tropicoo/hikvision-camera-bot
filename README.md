HikVision Camera Bot
=============================
Bot which sends snapshots from your HikVision camera(s).

Installation
------------

To install bot, simply `clone` repo and install dependencies using `pip`.
Make sure you have Python 3 installed.


```
git clone https://github.com/tropicoo/camerabot.git
pip install Pillow python-telegram-bot requests watchdog
```

Configuration
-------------
First of all you need to [create](https://core.telegram.org/bots#6-botfather)
Telegram Bot and obtain its token.

Before starting bot needs to be configured. Configuration is simply
stored in JSON format.

Edit `config.json`, which comes
with default template:
```json
{
  "telegram": {
    "token": "",
    "allowed_user_ids": []
  },
  "watchdog": {
    "enabled": false,
    "directory": ""
  },
  "log_level": "INFO",
  "camera_list": {
    "cam_1": {
      "description": "Kitchen Camera",
      "auth": {
        "user": "",
        "password": ""
      },
      "api_url": ""
    },
    "cam_2": {
      "description": "Basement Camera",
      "auth": {
        "user": "",
        "password": ""
      },
      "api_url": ""
    }
  }
}
```

To get things done follow next steps:
1. Put bot token to `token` key as string.
2. [Find](https://stackoverflow.com/a/32777943) your Telegram user id
and put it to `allowed_user_ids` list as integer value. Multiple ids can
be used, just separate them with a comma.
3. If you wish to monitor directory and send files to yourself when created,
enable `watchdog` by setting `enabled` to `true` and specify `directory`
path to be monitored e.g. `/tmp/watchdir`.
For example configure your camera to take and put snapshot on move detection
through FTP to watched folder. Watchdog looks for `on_create` events, sends
created file and deletes it.
4. HikVision camera settings are placed inside `camera_list`. Template
comes with two cameras. Preferable names of cameras are `cam_1`,
`cam_2`, `cam_3` etc. with any description.
5. Write authentication credentials in appropriate keys: `user` and `password`
for every camera you want to use.
6. Same for `api_url`, which should include protocol and api path e.g.
`http://192.168.10.10/Streaming/channels/102/picture?snapShotImageType=JPEG`

**Example configuration**
```json
{
  "telegram": {
    "token": "23546745:VjFIo2q34fjkKdasfds0kgSLnh",
    "allowed_user_ids": [
      1011111,
      5462243
    ]
  },
  "watchdog": {
    "enabled": true,
    "directory": "/tmp/watchdir"
  },
  "log_level": "INFO",
  "camera_list": {
    "cam_1": {
      "description": "Kitchen Camera",
      "auth": {
        "user": "admin",
        "password": "kjjhthOogv"
      },
      "api_url": "http://192.168.10.10/Streaming/channels/102/picture?snapShotImageType=JPEG"
    }
  }
}
```

Usage
=====
Simply run and see for welcome message in Telegram client.
```bash
python3 bot.py -c config.json
# or
chmod +x bot.py
./bot.py -c config.json
```

If you want to run in background and write to log file.
```bash
nohup python3 bot.py -c config.json &>/tmp/camerabot.log &
```
