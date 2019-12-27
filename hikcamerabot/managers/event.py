from hikcamerabot.config import get_result_queue
from hikcamerabot.constants import Events


class TaskEventManager:

    def __init__(self, event_queues):
        self._event_queues = event_queues

    def send_event(self, cam_id, payload):
        self._event_queues[cam_id].put(payload)

    def send_all(self, payload):
        for queue in self._event_queues.values():
            queue.put(payload)


class BaseResultEventManager:

    def __init__(self):
        self._queue_res = get_result_queue()

    def _msg_payload(self, event, **kwargs):
        self._queue_res.put({'event': event, **kwargs})


class AlertEventManager(BaseResultEventManager):

    def send_alert_msg(self, msg, cam_id, html=False, **kwargs):
        self._msg_payload(event=Events.ALERT_MSG,
                          msg=msg,
                          cam_id=cam_id,
                          html=html,
                          **kwargs)

    def send_alert_snapshot(self, detection_key, ts, img, alert_count,
                            cam_id, resized=False):
        self._msg_payload(event=Events.ALERT_SNAPSHOT,
                          detection_key=detection_key,
                          img=img,
                          ts=ts,
                          cam_id=cam_id,
                          alert_count=alert_count,
                          resized=resized)

    def send_alert_videos(self, videos, cam_id):
        self._msg_payload(event=Events.ALERT_VIDEO,
                          videos=videos,
                          cam_id=cam_id)


class LivestreamEventManager(BaseResultEventManager):

    def send_msg(self, msg, cam_id, html=False, **kwargs):
        self._msg_payload(event=Events.STREAM_MSG,
                          msg=msg,
                          cam_id=cam_id,
                          html=html,
                          **kwargs)
