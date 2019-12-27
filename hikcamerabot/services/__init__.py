import abc
import logging


class BaseService(metaclass=abc.ABCMeta):
    """Base Service Class."""

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        self._cls_name = self.__class__.__name__

        # e.g. alarm, stream (are used from constants.py module)
        self.type = None

    def __str__(self):
        return self._cls_name

    @abc.abstractmethod
    def start(self):
        pass

    @abc.abstractmethod
    def stop(self):
        pass

    @abc.abstractmethod
    def is_started(self):
        pass

    @abc.abstractmethod
    def is_enabled_in_conf(self):
        pass
