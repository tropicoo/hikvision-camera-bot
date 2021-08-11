import logging

from hikcamerabot.config.config import get_result_queue
from hikcamerabot.utils.task import create_task
from hikcamerabot.utils.utils import shallow_sleep_async


class ResultWorkerTask:

    def __init__(self, result_dispatcher, worker_id: int):
        self._log = logging.getLogger(self.__class__.__name__)
        self._result_dispatcher = result_dispatcher
        self._worker_id = worker_id
        self._res_queue = get_result_queue()

    async def run(self):
        while True:
            while not self._res_queue.empty():
                result_payload = await self._res_queue.get()
                try:
                    await self._result_dispatcher.dispatch(result_payload)
                except Exception:
                    self._log.exception(
                        'Unhandled exception in result worker %s. Context: %s',
                        self._worker_id, result_payload)
            await shallow_sleep_async(0.2)


class ResultWorkerManager:
    DEFAULT_WORKER_NUM = 4

    def __init__(self, dispatcher, worker_num: int = DEFAULT_WORKER_NUM):
        self._log = logging.getLogger(self.__class__.__name__)
        self._result_dispatcher = dispatcher
        self._worker_num = worker_num or self.DEFAULT_WORKER_NUM
        self._workers = []

    async def start_worker_tasks(self):
        for idx in range(self._worker_num):
            task_name = f'ResultWorkerTask_{idx}'
            self._log.debug('Starting %s', task_name)
            worker_task = create_task(
                ResultWorkerTask(self._result_dispatcher, idx).run(),
                task_name=task_name,
                logger=self._log,
                exception_message='Task %s raised an exception',
                exception_message_args=(task_name,),
            )
            self._workers.append(worker_task)
