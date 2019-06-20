HikVision Telegram Camera Bot
=============================
Bot which sends snapshots from your HikVision camera(s).

Installation
------------

To install the bot, simply `clone` repo and install dependencies using `pip3`.
Make sure you have [Python 3](https://www.python.org/downloads/) installed.


```
git clone https://github.com/tropicoo/hikvision-camera-bot.git
pip3 install Pillow python-telegram-bot requests watchdog xmltodict psutil
```

Also, to enable YouTube Live Stream, install the latest [ffmpeg](https://www.ffmpeg.org) build.

Configuration
-------------
First of all you need to [create Telegram Bot](https://core.telegram.org/bots#6-botfather)
 and obtain its token.

Before starting HikVision Telegram Camera Bot needs to be configured.
Configuration is simply stored in [JSON](https://spring.io/understanding/JSON#structure) 
format.

Copy default configuration file `config-template.json` with name you like e.g.
to `config.json` and edit, which comes with default template:
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
      "api": {
        "host": "",
        "auth": {
          "user": "",
          "password": ""
        },
        "endpoints": {
          "picture": "/Streaming/channels/102/picture?snapShotImageType=JPEG",
          "motion_detection": "ISAPI/System/Video/inputs/channels/1/motionDetection",
          "line_crossing_detection": "ISAPI/Smart/LineDetection/1",
          "alert_stream": "/ISAPI/Event/notification/alertStream"
        },
        "stream_timeout": 300
      },
      "alert": {
        "delay": 10,
        "motion_detection": {
          "enabled": false,
          "fullpic": true
        },
        "line_crossing_detection": {
          "enabled": false,
          "fullpic": true
        }
      },
      "live_stream": {
        "youtube": {
          "enabled": false,
          "channel": 101,
          "restart_period": 39600,
          "restart_pause": 10,
          "null_audio": false,
          "url": "rtmp://a.rtmp.youtube.com/live2",
          "key": ""
        }
      }
    },
    "cam_2": {
      "description": "Basement Camera",
      "api": {
        "host": "",
        "auth": {
          "user": "",
          "password": ""
        },
        "endpoints": {
          "picture": "/Streaming/channels/102/picture?snapShotImageType=JPEG",
          "motion_detection": "ISAPI/System/Video/inputs/channels/1/motionDetection",
          "line_crossing_detection": "ISAPI/Smart/LineDetection/1",
          "alert_stream": "/ISAPI/Event/notification/alertStream"
        },
        "stream_timeout": 300
      },
      "alert": {
        "delay": 10,
        "motion_detection": {
          "enabled": false,
          "fullpic": true
        },
        "line_crossing_detection": {
          "enabled": false,
          "fullpic": true
        }
      },
      "live_stream": {
        "youtube": {
          "enabled": false,
          "channel": 101,
          "restart_period": 39600,
          "restart_pause": 10,
          "null_audio": false,
          "url": "rtmp://a.rtmp.youtube.com/live2",
          "key": ""
        }
      }
    }
  }
}
```

To get things done follow the next steps:
1. Put the obtained bot token to `token` key as string.
2. [Find](https://stackoverflow.com/a/32777943) your Telegram user id
and put it to `allowed_user_ids` list as integer value. Multiple ids can
be used, just separate them with a comma.
3. If you wish to monitor directory and send files to yourself when created,
enable `watchdog` by setting `enabled` to `true` and specify `directory`
path to be monitored e.g. `/tmp/watchdir`. Make sure that directory exists.
For example configure your camera to take and put snapshot on move detection
through FTP to watched folder. Watchdog looks for `on_create` events, sends
created file and deletes it.
4. HikVision camera settings are placed inside the `camera_list` section. Template
comes with two cameras. Preferable names of cameras are `cam_1`,
`cam_2`, `cam_3` and so on with any description.
5. Write authentication credentials in appropriate keys: `user` and `password`
for every camera you want to use.
6. Same for `host`, which should include protocol e.g. `http://192.168.10.10`
7. In `alert` section you can enable sending picture on alert (Motion Detection 
and/or Line Crossing Detection).
Configure `delay` setting in seconds between pushing alert pictures.
To send resized picture change `fullpic` to `false`.
8. To enable YouTube Live Stream (experimental), fill the `youtube` section with
valid parameters:
    ```python
          "enabled": false, # start stream during bot start (true or false)
          "channel": 101, # camera channel. 101 is main stream, 102 is substream.
          "restart_period": 39600, # stream restart period in seconds
          "restart_pause": 10, # stream pause before starting on restart
          "null_audio": false, # enable fake silent audio (for cameras without mics)
          "url": "rtmp://a.rtmp.youtube.com/live2", # YouTube rtmp server
          "key": "aaaa-vvvv-bbbb-cccc-zzzz" # YouTube Live Stream key.
    ```
    > YouTube Live Stream server/key is availabe at https://www.youtube.com/live_dashboard.

    > To enable stream in Telegram, simply use available commands 
    `/yt_stream_on_<cam_id>, /yt_stream_off_<cam_id>`
    
    > To kill the bot from the terminal with enabled YouTube Live Stream 
    instead of invoking the `/stop` command from the Telegram, kill
    it with its process group `kill -TERM -<PID>` else ffmpeg process
    will be still alive.

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
      "api": {
        "host": "http://192.168.10.10",
        "auth": {
          "user": "admin",
          "password": "kjjhthOogv"
        },
        "endpoints": {
          "picture": "/Streaming/channels/102/picture?snapShotImageType=JPEG",
          "motion_detection": "ISAPI/System/Video/inputs/channels/1/motionDetection",
          "line_crossing_detection": "ISAPI/Smart/LineDetection/1",
          "alert_stream": "/ISAPI/Event/notification/alertStream"
        },
        "stream_timeout": 300
      },
      "alert": {
        "delay": 10,
        "motion_detection": {
          "enabled": false,
          "fullpic": true
        },
        "line_crossing_detection": {
          "enabled": false,
          "fullpic": true
        }
      },
      "live_stream": {
        "youtube": {
          "enabled": false,
          "channel": 101,
          "restart_period": 39600,
          "restart_pause": 10,
          "null_audio": false,
          "url": "rtmp://a.rtmp.youtube.com/live2",
          "key": "aaaa-vvvv-bbbb-cccc-zzzz"
        }
      }
    }
  }
}
```

Usage
=====
Simply run and see for welcome message in Telegram client.
> Note: This will log the output to the stdout/stderr (your terminal). Closing
the terminal will shutdown the bot.
```bash
python3 bot.py -c config.json

# Or make the script executable by adding 'x' flag
chmod +x bot.py
./bot.py -c config.json
```

If you want to run the bot in the background use the following commands
```bash
# With writing to the log file
nohup python3 bot.py -c config.json &>/tmp/camerabot.log &

# Without writing to the log file
nohup python3 bot.py --config config.json &>- &
```

Misc
=====
If you're on the Raspberry Pi, you can easily add bot execution to the startup.

Simply edit the `/etc/rc.local` add the following line before the last one
(which is `exit 0`):
```bash
# The path '/home/pi/hikvision-camera-bot/config.json' is an absolute path to the config file (same for 'bot.py')
nohup python3 /home/pi/hikvision-camera-bot/bot.py --config /home/pi/hikvision-camera-bot/config.json &>- &
```
