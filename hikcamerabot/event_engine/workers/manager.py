import logging
from typing import TYPE_CHECKING

from hikcamerabot.event_engine.workers.tasks import ResultWorkerTask
from hikcamerabot.utils.task import create_task

if TYPE_CHECKING:
    from hikcamerabot.event_engine.dispatchers.outbound import OutboundEventDispatcher


class ResultWorkerManager:
    _DEFAULT_WORKER_NUM = 4

    def __init__(
        self,
        dispatcher: 'OutboundEventDispatcher',
        worker_num: int = _DEFAULT_WORKER_NUM,
    ):
        self._log = logging.getLogger(self.__class__.__name__)
        self._outbound_dispatcher = dispatcher
        self._workers = []

        if worker_num <= 0:
            self._worker_num = self._DEFAULT_WORKER_NUM
        else:
            self._worker_num = worker_num

    def start_worker_tasks(self) -> None:
        for idx in range(1, self._worker_num + 1):
            task_name = f'ResultWorkerTask_{idx}'
            self._log.debug('Starting %s', task_name)
            self._workers.append(
                create_task(
                    ResultWorkerTask(self._outbound_dispatcher, idx).run(),
                    task_name=task_name,
                    logger=self._log,
                    exception_message='Task "%s" raised an exception',
                    exception_message_args=(task_name,),
                )
            )
