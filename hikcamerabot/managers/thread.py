from threading import Event


class ThreadManager:
    def __init__(self, threads):
        self._threads = threads
        self._running_threads = []

        self._should_run = Event()
        self._should_run.set()

    def start_threads(self):
        for thr in self._threads:
            thr.add_run_trigger(run_trigger=self._should_run)
            thr.start()
            self._running_threads.append(thr)

    def stop_threads(self):
        self._should_run.clear()
