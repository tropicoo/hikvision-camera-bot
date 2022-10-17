import logging
from typing import TYPE_CHECKING

from hikcamerabot.enums import Detection
from hikcamerabot.services.alarm.tasks.notifications import (
    AlarmPicNotificationTask,
    AlarmTextMessageNotificationTask,
    AlarmVideoGifNotificationTask,
)
from hikcamerabot.utils.task import create_task

if TYPE_CHECKING:
    from hikcamerabot.services.alarm import AlarmService


class AlertNotifier:
    ALARM_NOTIFICATION_TASKS = (
        AlarmTextMessageNotificationTask,
        AlarmVideoGifNotificationTask,
        AlarmPicNotificationTask,
    )

    def __init__(self, service: 'AlarmService') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._service = service

    def notify(self, detection_type: Detection) -> None:
        for task_cls in self.ALARM_NOTIFICATION_TASKS:
            cls_name = task_cls.__name__
            self._log.debug('Notifying with %s', cls_name)
            task = task_cls(service=self._service, detection_type=detection_type)
            create_task(
                task.run(),
                task_name=cls_name,
                logger=self._log,
                exception_message='Task %s raised an exception',
                exception_message_args=(cls_name,),
            )
