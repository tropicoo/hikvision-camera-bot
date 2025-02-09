import logging
from typing import TYPE_CHECKING

from hikcamerabot.enums import DetectionType
from hikcamerabot.services.alarm.camera.tasks.notifications import (
    AlarmPicNotificationTask,
    AlarmTextMessageNotificationTask,
    AlarmVideoGifNotificationTask,
)
from hikcamerabot.utils.task import create_task

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam


class AlarmNotifier:
    ALARM_NOTIFICATION_TASKS = (
        AlarmTextMessageNotificationTask,
        AlarmVideoGifNotificationTask,
        AlarmPicNotificationTask,
    )

    def __init__(self, cam: 'HikvisionCam', alert_count: int) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam = cam
        self._alert_count = alert_count

    def notify(self, detection_type: DetectionType) -> None:
        for task_cls in self.ALARM_NOTIFICATION_TASKS:
            cls_name = task_cls.__name__
            self._log.info(
                '[%s - %s] Notifying with %s',
                self._cam.id,
                self._cam.description,
                cls_name,
            )
            task = task_cls(
                detection_type=detection_type,
                cam=self._cam,
                alert_count=self._alert_count,
            )
            create_task(
                task.run(),
                task_name=cls_name,
                logger=self._log,
                exception_message='Task "%s" raised an exception',
                exception_message_args=(cls_name,),
            )
