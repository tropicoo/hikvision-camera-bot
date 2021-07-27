"""Telegram bot commands module."""

from typing import Callable, Union

import hikcamerabot.callbacks as cb


def setup_commands() -> tuple[dict, dict[Union[tuple[str, ...], str], Callable]]:
    tpl_cmds = {
        'General': {
            'commands': {
                'cmds_{0}': cb.cmds,
                'getpic_{0}': cb.cmd_getpic,
                'getfullpic_{0}': cb.cmd_getfullpic,
            },
        },
        'Motion Detection': {
            'commands': {
                'md_on_{0}': cb.cmd_motion_detection_on,
                'md_off_{0}': cb.cmd_motion_detection_off,
            },
        },
        'Line Crossing Detection': {
            'commands': {
                'ld_on_{0}': cb.cmd_line_detection_on,
                'ld_off_{0}': cb.cmd_line_detection_off,
            },
        },
        'Intrusion (Field) Detection': {
            'commands': {
                'intr_on_{0}': cb.cmd_intrusion_detection_on,
                'intr_off_{0}': cb.cmd_intrusion_detection_off,
            },
        },
        'Alert Service': {
            'commands': {
                'alert_on_{0}': cb.cmd_alert_on,
                'alert_off_{0}': cb.cmd_alert_off,
            },
        },
        'YouTube Stream': {
            'commands': {
                'yt_on_{0}': cb.cmd_stream_yt_on,
                'yt_off_{0}': cb.cmd_stream_yt_off,
            },
        },
        'Icecast Stream': {
            'commands': {
                'icecast_on_{0}': cb.cmd_stream_icecast_on,
                'icecast_off_{0}': cb.cmd_stream_icecast_off,
            },
        },
    }

    global_cmds = {
        ('start', 'help'): cb.cmd_help,
        'stop': cb.cmd_stop,
        'list': cb.cmd_list_cams,
    }

    return tpl_cmds, global_cmds
