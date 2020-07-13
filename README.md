# Hikvision Telegram Camera Bot
Telegram Bot which sends snapshots from your Hikvision camera(s).

## Features
1. Auto-sending snapshots on **Motion**, **Line Crossing** and **Intrusion (Field) Detection**
2. Sending full/resized snapshots on request
3. Sending so-called Telegram video-gifs on alert events from paragraph #1
4. YouTube and Icecast direct or re-encoded streaming


![frames](img/screenshot-1.png)

# Installation

To install Hikvision Telegram Camera Bot, simply `clone` repo and install 
dependencies using `pip3`.

1. Make sure you have at least **Python 3.6** version installed
    ```shell script
    python3 -V
    Python 3.7.3
    ```
2. Install
    ```shell script
    git clone https://github.com/tropicoo/hikvision-camera-bot.git
    cd hikvision-camera-bot
    sudo pip3 install -r requirements.txt
    sudo apt update && sudo apt install ffmpeg
    ```

# Configuration
Configuration is simply stored in JSON format.

## Quick Setup
1. [Create and start Telegram Bot](https://core.telegram.org/bots#6-botfather)
 and get its API token
2. Copy 3 default configuration files with predefined templates:
    
    ```bash
    cp config-template.json config.json
    cp encoding_templates-template.json encoding_templates.json
    cp livestream_templates-template.json livestream_templates.json
    ```
3. Edit **config.json**:
    - Put the obtained bot API token to `token` key as string
    - [Find](https://stackoverflow.com/a/32777943) your Telegram user id
    and put it to `allowed_user_ids` list as integer value. Multiple ids can
    be used, just separate them with a comma
    - Hikvision camera settings are placed inside the `camera_list` section. Template
    comes with two cameras

        **Camera names should start with `cam_` prefix and end with 
        digit suffix**: `cam_1`, `cam_2`, `cam_<digit>` and so on with any description.

    - Write authentication credentials in appropriate keys: `user` and `password`
    for every camera you want to use
    - Same for `host`, which should include protocol e.g. `http://192.168.10.10`
    - In `alert` section you can enable sending picture on alert (Motion, 
    Line Crossing and Intrusion (Field) Detection). Configure `delay` setting 
    in seconds between pushing alert pictures. To send resized picture change 
    `fullpic` to `false`

### config.json example
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
          "stream_timeout": 300
        },
        "alert": {
          "delay": 10,
          "video_gif": {
            "enabled": true,
            "channel": 102,
            "record_time": 5,
            "tmp_storage": "/tmp",
            "loglevel": "quiet",
            "rtsp_transport_type": "tcp"
          },
          "motion_detection": {
            "enabled": false,
            "fullpic": true
          },
          "line_crossing_detection": {
            "enabled": false,
            "fullpic": true
          },
          "intrusion_detection": {
            "enabled": false,
            "fullpic": false
          }
        },
        "livestream": {
          "youtube": {
            "enabled": false,
            "livestream_template": "tpl_kitchen",
            "encoding_template": "x264.kitchen",
          },
          "icecast": {
            "enabled": false,
            "livestream_template": "tpl_kitchen",
            "encoding_template": "vp9.kitchen"
          }
        }
      }
    }
  }
  ```
</details>

# Usage
## Launch by using Docker and Docker Compose (preferable)
1. Set your timezone by editing `docker-compose.yaml` file.
Currently there is Ukrainian timezone because I live there.
Look for your timezone here http://www.timezoneconverter.com/cgi-bin/zoneinfo.
If you want to use default UTC time format, just completely remove these 
two lines or set Greenwich Mean Time timezone `"TZ=GMT"`
    ```yaml
    environment:
      - "TZ=Europe/Kiev"
    ```
2. Build image and run container in detached mode
    ```bash
    sudo docker-compose build && sudo docker-compose up -d && sudo docker-compose logs -f --tail=1000
    ```

## Direct launch from terminal 
Simply run and wait for welcome message in your Telegram client.
> Note: This will log the output to the stdout/stderr (your terminal). Closing
the terminal will shutdown the bot.
```bash
python3 bot.py
```

If you want to run the bot in the background use the following commands
```bash
# With writing to the log file
nohup python3 bot.py &>/tmp/camerabot.log &

# Without writing to the log file
nohup python3 bot.py &>- &
```

# Commands
| Command | Description |
|---|---|
| `/start` | Start the bot (one-time action during first start) and show help |
| `/stop` | Stop the bot (terminate all processes) |
| `/help` | Show help message |
| `/list` | List all your cameras with commands |
| `/cmds_cam_*` | List commands for particular camera |
| `/getpic_cam_*` | Get resized picture from your Hikvision camera  |
| `/getfullpic_cam_*` | Get full-sized picture from your Hikvision camera |
| `/md_on_cam_*` | Enable Motion Detection |
| `/md_off_cam_*` | Disable Motion Detection |
| `/ld_on_cam_*` | Enable Line Crossing Detection |
| `/ld_off_cam_*` | Disable Line Crossing Detection |
| `/intr_on_cam_*` | Enable Intrusion (Field) Detection |
| `/intr_off_cam_*` | Disable Intrusion (Field) Detection |
| `/alert_on_cam_*` | Enable Alert (Alarm) mode. It means it will send respective alert to your account in Telegram |
| `/alert_off_cam_*` | Disable Alert (Alarm) mode, no alerts will be sent when something detected |
| `/yt_on_cam_*` | Enable YouTube stream |
| `/yt_off_cam_*` | Disable YouTube stream |
| `/icecast_on_cam_*` | Enable Icecast stream |
| `/icecast_off_cam_*` | Disable Icecast stream |

`*` - camera id (digit) e.g. `cam_1`.

#  Advanced Configuration
1. To enable YouTube Live Streams (experimental), enable it in the `youtube` key.

    | Parameter | Value | Description |
    |---|---|---|
    | `"enabled"` | `false` | set `true` to start stream during bot start |
    | `"livestream_template"` | `"tpl_kitchen"` | stream template, read below |
    | `"encoding_template"` | `"x264.kitchen"` | stream template, read below |
    
    **Livestream templates**
    
    To start particular livestream, user needs to set both *livestream* and
    *encoding* templates with stream settings and encoding type/arguments.
    
    Encoding templates
    
    `direct` means that video stream will not be re-encoded (transcoded) and will
    be sent to YouTube/Icecast servers "as is", only audio can be disabled.
    
    `x264` or `vp9` means that video stream will be re-encoded on your machine/server
    where bot is running using respective encoding codecs.
    
    User can create its own templates in file named `livestream_templates.json` 
    and `encoding_templates.json`.
    
    Default dummy template file is named `livestream_templates_template.json` 
    (not very funny name but anyway) which should be copied or renamed to 
    `livestream_templates.json`.
    
    Same for `encoding_templates-template.json` -> `encoding_templates.json`
    
    <details>
      <summary>livestream_templates-template.json</summary>

      ```json
      {
        "youtube": {
          "tpl_kitchen": {
            "channel": 101,
            "restart_period": 39600,
            "restart_pause": 10,
            "url": "rtmp://a.rtmp.youtube.com/live2",
            "key": "xxxx-xxxx-xxxx-xxxx"
          },
          "tpl_basement": {
            "channel": 101,
            "restart_period": 39600,
            "restart_pause": 10,
            "url": "rtmp://a.rtmp.youtube.com/live2",
            "key": "xxxx-xxxx-xxxx-xxxx"
          }
        },
        "icecast": {
          "tpl_kitchen": {
            "channel": 101,
            "restart_period": 39600,
            "restart_pause": 10,
            "ice_stream": {
              "ice_genre": "333Default",
              "ice_name": "222Default",
              "ice_description": "111Default",
              "ice_public": 0,
              "url": "icecast://source@192.168.10.1:8000/video.webm",
              "password": "hackme",
              "content_type": "video/webm"
            }
          },
          "tpl_basement": {
            "channel": 101,
            "restart_period": 39600,
            "restart_pause": 10,
            "ice_stream": {
              "ice_genre": "333Default",
              "ice_name": "222Default",
              "ice_description": "111Default",
              "ice_public": 0,
              "url": "icecast://source@192.168.10.2:8000/video.webm",
              "password": "hackme",
              "content_type": "video/webm"
            }
          }
        },
        "twitch": {
          "tpl_kitchen": {
            "channel": 101,
            "restart_period": 39600,
            "restart_pause": 10,
            "url": "rtmp://live-waw.twitch.tv/app",
            "key": ""
          },
          "tpl_basement": {
            "channel": 101,
            "restart_period": 39600,
            "restart_pause": 10,
            "url": "rtmp://live-waw.twitch.tv/app",
            "key": ""
          }
        }
      }
      ```
    </details>
    
    Where:
    
    | Parameter | Value | Description |
    |---|---|---|
    | `channel` | `101` | camera channel. 101 is main stream, 102 is substream. |
    | `restart_period` | `39600` | stream restart period in seconds |
    | `restart_pause` | `10` | stream pause before starting on restart |
    | `url` | `"rtmp://a.rtmp.youtube.com/live2"` | YouTube rtmp server |
    | `key` | `"aaaa-bbbb-cccc-dddd"` | YouTube Live Streams key. |
    | `ice_genre` | `"Default"` | Icecast stream genre |
    | `ice_name` | `"Default"` | Icecast stream name |
    | `ice_description` | `"Default"` | Icecast stream description |
    | `ice_public` | `0` | Icecast public switch, default 0 |
    | `url` | `"icecast://source@x.x.x.x:8000/video.webm"` | Icecast server URL, Port and media mount point |
    | `password` | `"xxxx"` | Icecast authentication password |
    | `content_type` | `"video`/webm" | FFMPEG content-type for Icecast stream |
    
    <details>
      <summary>encoding_templates-template.json</summary>

      ```json
      {
        "x264": {
          "kitchen": {
            "null_audio": false,
            "loglevel": "quiet",
            "vcodec": "libx264",
            "acodec": "aac",
            "format": "flv",
            "rtsp_transport_type": "tcp",
            "pix_fmt": "yuv420p",
            "pass_mode": 1,
            "framerate": 25,
            "preset": "superfast",
            "average_bitrate": "1000K",
            "maxrate": "3000k",
            "bufsize": "6000k",
            "tune": "zerolatency",
            "scale": {
              "enabled": true,
              "width": 640,
              "height": -1,
              "format": "yuv420p"
            }
          },
          "basement": {
            "null_audio": false,
            "loglevel": "quiet",
            "vcodec": "libx264",
            "acodec": "aac",
            "format": "flv",
            "rtsp_transport_type": "tcp",
            "pix_fmt": "yuv420p",
            "pass_mode": 1,
            "framerate": 25,
            "preset": "superfast",
            "average_bitrate": "1000K",
            "maxrate": "3000k",
            "bufsize": "6000k",
            "tune": "zerolatency",
            "scale": {
              "enabled": true,
              "width": 640,
              "height": -1,
              "format": "yuv420p"
            }
          }
        },
        "vp9": {
          "kitchen": {
            "null_audio": false,
            "loglevel": "info",
            "vcodec": "libvpx-vp9",
            "acodec": "libopus",
            "format": "webm",
            "rtsp_transport_type": "tcp",
            "pix_fmt": "yuv420p",
            "pass_mode": 1,
            "framerate": 10,
            "average_bitrate": "1000K",
            "maxrate": "2000k",
            "bufsize": "4000k",
            "deadline": "realtime",
            "speed": 5,
            "scale": {
              "enabled": true,
              "width": 640,
              "height": -1,
              "format": "yuv420p"
            }
          },
          "basement": {
            "null_audio": false,
            "loglevel": "info",
            "vcodec": "libvpx-vp9",
            "acodec": "libopus",
            "format": "webm",
            "rtsp_transport_type": "tcp",
            "pix_fmt": "yuv420p",
            "pass_mode": 1,
            "framerate": 10,
            "average_bitrate": "1000K",
            "maxrate": "2000k",
            "bufsize": "4000k",
            "deadline": "realtime",
            "speed": 5,
            "scale": {
              "enabled": true,
              "width": 640,
              "height": -1,
              "format": "yuv420p"
            }
          }
        },
        "direct": {
          "kitchen": {
            "null_audio": false,
            "loglevel": "quiet",
            "vcodec": "copy",
            "acodec": "aac",
            "format": "flv",
            "rtsp_transport_type": "tcp"
          },
          "basement": {
            "null_audio": false,
            "loglevel": "quiet",
            "vcodec": "copy",
            "acodec": "aac",
            "format": "flv",
            "rtsp_transport_type": "tcp"
          }
        }
      }
      ```
    </details>
    
    Where:
    
    | Parameter | Value | Description |
    |---|---|---|
    | `null_audio` | `false` | enable fake silent audio (for cameras without mics) |
    | `url` | `"rtmp://a.rtmp.youtube.com/live2"` | YouTube rtmp server |
    | `key` | `"aaaa-bbbb-cccc-dddd"` | YouTube Live Streams key |
    | `loglevel` | `"quiet"` | ffmpeg log levels, default "quiet" |
    | `pix_fmt` | `"yuv420p"` | pixel format, Hikvision streams in yuvj420p |
    | `framerate` | `25` | encode framerate, YouTube will re-encode any to 30 anyway |
    | `preset` | `"superfast"` | libx264 predefined presets, more here https://trac.ffmpeg.org/wiki/Encode/H.264 |
    | `maxrate` | `"3000k"` | max variable bitrate |
    | `bufsize` | `"2000k"` | rate control buffer |
    | `tune` | `"zerolatency"` | tune for zero latency |
    | `scale` | \<key\> | re-scale video size |
    | `enabled` | `true` | false to disable and re-encode with source width and height |
    | `width` | `640` | width |
    | `height` | `-1` | height, -1 means will be automatically determined |
    | `format` | `"yuv420p"` | pixel format |
    
    > YouTube Live Streams server/key is availabe at https://www.youtube.com/live_dashboard.

    > To enable stream in Telegram, simply use available commands 
    `/yt_on_<cam_id>, /yt_off_<cam_id>`

    > To kill the bot from the terminal with enabled YouTube Live Streams 
    instead of invoking the `/stop` command from the Telegram, kill
    it with its process group `kill -TERM -<PID>` else ffmpeg process
    will be still alive.
   
2. (Deprecated) If you wish to monitor directory and send files to yourself when created,
enable `watchdog` by setting `enabled` to `true` and specify `directory`
path to be monitored e.g. `/tmp/watchdir`. Make sure that directory exists.
For example configure your camera to take and put snapshot on move detection
through FTP to watched folder. Watchdog looks for `on_create` events, sends
created file and deletes it.
