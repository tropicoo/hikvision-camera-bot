import abc
import logging
from typing import Union


DispatchTypeDict = dict[
    str, Union['AbstractTaskEventHandler', 'AbstractResultEventHandler']]


class AbstractDispatcher(metaclass=abc.ABCMeta):
    DISPATCH: DispatchTypeDict = {}

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        self._dispatch = {k: v() for k, v in self.DISPATCH.items()}

    @abc.abstractmethod
    async def dispatch(self, data: dict):
        pass
