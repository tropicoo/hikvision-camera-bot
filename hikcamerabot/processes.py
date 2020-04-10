import logging
import multiprocessing

from hikcamerabot.config import get_result_queue
from hikcamerabot.constants import Alarms
from hikcamerabot.dispatchers.event import EventDispatcher
from hikcamerabot.services.threads import (ServiceAlarmPusherThread,
                                           ServiceStreamerThread)
from hikcamerabot.utils import shallow_sleep


class CameraSupervisorProc(multiprocessing.Process):
    """Supervisor process per camera instance."""

    SERVICE_THREADS = {
        ServiceStreamerThread.type: ServiceStreamerThread,
        ServiceAlarmPusherThread.type: ServiceAlarmPusherThread}

    def __init__(self, camera, queue_in):
        super().__init__()
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam = camera
        self._dispatcher = EventDispatcher(self._cam)
        self._queue_in = queue_in
        self._queue_res = get_result_queue()
        self._alert_pusher_thread = None

    def _start_thread(self, thread, service):
        thread = thread(cam=self._cam, service=service)
        thread.start()

        # Kostyl for self._check_videos
        if thread.service.name == Alarms.ALARM:
            self._alert_pusher_thread = thread

    def _start_enabled_services(self):
        """Start camera services enabled in conf."""
        self._cam.service_manager.start_services(enabled_in_conf=True)

        # TODO: Rethink this old logic
        for svc in self._cam.service_manager.get_services():
            self._start_thread(thread=self.SERVICE_THREADS.get(svc.type),
                               service=svc)

    def stop(self):
        # TODO: Is this needed?
        self._cam.service_manager.stop_services()

    def _check_videos(self):
        """Very kostyl because `ServiceAlarmPusherThread._process_chunks`
        method is blocking.
        """
        recorded_videos = self._cam.video_manager.get_videos()
        if recorded_videos:
            self._alert_pusher_thread._event_manager.send_alert_videos(
                videos=recorded_videos,
                cam_id=self._cam.id)

    def run(self):
        """Run supervisor process."""
        self._start_enabled_services()
        # proc.terminate() will terminate this loop
        while True:
            self._check_videos()
            while not self._queue_in.empty():
                data = self._queue_in.get()
                result = self._dispatcher.handle(data)
                self._queue_res.put(result)
            shallow_sleep()
