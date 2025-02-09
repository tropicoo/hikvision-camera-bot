"""Telegram bot commands module."""

from collections.abc import Callable

import hikcamerabot.callbacks as cb
from hikcamerabot.enums import CmdSectionType


def setup_commands() -> tuple[dict, dict[list[str] | str, Callable]]:
    tpl_cmds = {
        CmdSectionType.general: {
            'commands': {
                'cmds_{0}': cb.cmds,
                'getpic_{0}': cb.cmd_getpic,
                'getfullpic_{0}': cb.cmd_getfullpic,
                'getvideo_{0}': cb.cmd_getvideo,
                'getvideor_{0}': cb.cmd_getvideor,
            },
        },
        CmdSectionType.infrared: {
            'commands': {
                'ir_on_{0}': cb.cmd_ir_on,
                'ir_off_{0}': cb.cmd_ir_off,
                'ir_auto_{0}': cb.cmd_ir_auto,
            },
        },
        CmdSectionType.motion_detection: {
            'commands': {
                'md_on_{0}': cb.cmd_motion_detection_on,
                'md_off_{0}': cb.cmd_motion_detection_off,
            },
        },
        CmdSectionType.line_detection: {
            'commands': {
                'ld_on_{0}': cb.cmd_line_detection_on,
                'ld_off_{0}': cb.cmd_line_detection_off,
            },
        },
        CmdSectionType.intrusion_detection: {
            'commands': {
                'intr_on_{0}': cb.cmd_intrusion_detection_on,
                'intr_off_{0}': cb.cmd_intrusion_detection_off,
            },
        },
        CmdSectionType.alert_service: {
            'commands': {
                'alert_on_{0}': cb.cmd_alert_on,
                'alert_off_{0}': cb.cmd_alert_off,
            },
        },
        CmdSectionType.stream_youtube: {
            'commands': {
                'yt_on_{0}': cb.cmd_stream_yt_on,
                'yt_off_{0}': cb.cmd_stream_yt_off,
            },
        },
        CmdSectionType.stream_telegram: {
            'commands': {
                'tg_on_{0}': cb.cmd_stream_tg_on,
                'tg_off_{0}': cb.cmd_stream_tg_off,
            },
        },
        CmdSectionType.stream_icecast: {
            'commands': {
                'icecast_on_{0}': cb.cmd_stream_icecast_on,
                'icecast_off_{0}': cb.cmd_stream_icecast_off,
            },
        },
    }

    global_cmds = {
        'start': cb.cmd_help,
        'help': cb.cmd_help,
        'stop': cb.cmd_stop,
        'groups': cb.cmd_list_groups,
        'list_cams': cb.cmd_list_cams,
        'version': cb.cmd_app_version,
        'ver': cb.cmd_app_version,
        'v': cb.cmd_app_version,
    }

    return tpl_cmds, global_cmds
