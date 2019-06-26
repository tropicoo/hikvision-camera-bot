HikVision Telegram Camera Bot
=============================
Bot which sends snapshots from your HikVision camera(s).

Installation
------------

To install HikVision Telegram Camera Bot, simply `clone` repo and install 
dependencies using `pip3`.
Make sure you have [Python 3](https://www.python.org/downloads/) installed.


```
git clone https://github.com/tropicoo/hikvision-camera-bot.git
pip3 install Pillow python-telegram-bot requests watchdog xmltodict psutil

# To be able to use YouTube Livestream install ffmpeg
sudo apt-get install ffmpeg
```

Configuration
-------------
First of all you need to [create Telegram Bot](https://core.telegram.org/bots#6-botfather)
 and obtain its token.

Before starting HikVision Telegram Camera Bot needs to be configured.
Configuration is simply stored in JSON format.

Copy default configuration file with predefined template `config-template.json`
 to `config.json` and edit it:
<details>
  <summary>config-template.json</summary>
  
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
          "host": "http://192.168.0.1",
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
        "livestream": {
          "youtube": {
            "enabled": false,
            "template": "direct.tpl_kitchen"
          }
        }
      },
      "cam_2": {
        "description": "Basement Camera",
        "api": {
          "host": "http://192.168.0.2",
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
            "template": "transcode.tpl_basement"
          }
        }
      }
    }
  }
  ```
</details>

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
8. To enable YouTube Live Stream (experimental), enable it in the `youtube` key.
    ```python
          "enabled": false, # set `true` to start stream during bot start
          "template": "direct.tpl_kitchen" # stream template, read below
    ```
    
    *Livestream templates*
    To start particular livestream, user needs to set which already template 
    should be used for streaming (basically template contains ffmpeg arguments).
    There are two template categories: `direct` and `transcode`.
    
    `direct` means that video stream will not be re-encoded (transcoded) and will
    be sent to YouTube servers "as is", only audio can be disabled.
    
    `transcode` means that video stream will be re-encoded on your machine/server
    where bot is running.
    
    User can create its own templates in file named `livestream_templates.json`.
    Predefined template names are starting with `tpl_` e.g. `tpl_kitchen`, but
    any can be used.
    
    Default dummy template file is named `livestream_templates_template.json` 
    (not very funny name but anyway) which should be copied or renamed to 
    `livestream_templates.json`.
    
    <details>
      <summary>livestream_templates.json</summary>
      
      ```json
      {
        "youtube": {
          "direct": {
            "tpl_kitchen": {
              "channel": 101,
              "restart_period": 39600,
              "restart_pause": 10,
              "null_audio": false,
              "url": "rtmp://a.rtmp.youtube.com/live2",
              "key": "aaaa-bbbb-cccc-dddd"
            },
            "tpl_basement": {
            }
          },
          "transcode": {
            "tpl_kitchen": {
              "channel": 101,
              "restart_period": 39600,
              "restart_pause": 10,
              "null_audio": false,
              "url": "rtmp://a.rtmp.youtube.com/live2",
              "key": "aaaa-bbbb-cccc-dddd",
              "encode": {
                "pix_fmt": "yuv420p",
                "framerate": 25,
                "preset": "superfast",
                "maxrate": "3000k",
                "bufsize": "2000k",
                "tune": "zerolatency",
                "scale": {
                  "enabled": true,
                  "width": 640,
                  "height": -1,
                  "format": "yuv420p"
                }
              }
            }
          }
        }
      }
      ```
    </details>
    
    Where:
    ```python
          "channel": 101, # camera channel. 101 is main stream, 102 is substream.
          "restart_period": 39600, # stream restart period in seconds
          "restart_pause": 10, # stream pause before starting on restart
          "null_audio": false, # enable fake silent audio (for cameras without mics)
          "url": "rtmp://a.rtmp.youtube.com/live2", # YouTube rtmp server
          "key": "aaaa-bbbb-cccc-dddd" # YouTube Live Stream key.
          "encode": { # key with transcode configuration
            "pix_fmt": "yuv420p", # pixel format, HikVision streams in yuvj420p
            "framerate": 25, # encode framerate, YouTube will re-encode any to 30 anyway
            "preset": "superfast", # libx264 predefined presets, more here https://trac.ffmpeg.org/wiki/Encode/H.264
            "maxrate": "3000k", # max variable bitrate
            "bufsize": "2000k", # rate control buffer
            "tune": "zerolatency", # tune for zero latency
            "scale": { # re-scale video size
              "enabled": true, # false to disable and re-encode with source width and height
              "width": 640, # width
              "height": -1, # height, -1 means will be automatically determined
              "format": "yuv420p" # pixel format
            }
          }
    ```
    
    > YouTube Live Stream server/key is availabe at https://www.youtube.com/live_dashboard.

    > To enable stream in Telegram, simply use available commands 
    `/yt_on_<cam_id>, /yt_off_<cam_id>`
    
    > To kill the bot from the terminal with enabled YouTube Live Stream 
    instead of invoking the `/stop` command from the Telegram, kill
    it with its process group `kill -TERM -<PID>` else ffmpeg process
    will be still alive.

**Example configuration**
<details>
  <summary>Expand</summary>
  
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
            "template": "direct.tpl_kitchen",
          }
        }
      }
    }
  }
  ```
</details>
  
Usage
=====
Simply run and wait for welcome message in your Telegram client.
> Note: This will log the output to the stdout/stderr (your terminal). Closing
the terminal will shutdown the bot.
```bash
python3 bot.py -c config.json

# Or make the script executable by adding 'x' flag (it should be already with it)
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
