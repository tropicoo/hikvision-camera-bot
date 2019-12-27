from threading import Thread


class CommonThread(Thread):
    def __init__(self):
        super().__init__()
        self._run_trigger = None

    def add_run_trigger(self, run_trigger):
        self._run_trigger = run_trigger
