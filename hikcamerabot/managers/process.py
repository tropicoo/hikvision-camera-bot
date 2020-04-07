"""Processes managers module."""

import logging

from hikcamerabot.camera import HikvisionCam
from hikcamerabot.config import get_result_queue
from hikcamerabot.processes import CameraSupervisorProc


class CameraProcessManager:
    """Camera Process Manager Class."""

    def __init__(self, cam_registry, event_q):
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.debug('Initializing %r', self)

        self.cam_registry = cam_registry
        self._event_queues = event_q
        self._result_queue = get_result_queue()

        self._procs = []

    def start_processes(self):
        """Start Updater Processes."""
        for cam_id, meta in self.cam_registry.get_all().items():
            cam = HikvisionCam(id=cam_id, conf=meta['conf'])
            proc = CameraSupervisorProc(camera=cam,
                                        queue_in=self._event_queues[cam_id])
            self._log.debug('Starting %s', proc)
            proc.start()
            self._procs.append(proc)

    def stop_processes(self):
        for proc in self._procs:
            proc.terminate()
            proc.join()
