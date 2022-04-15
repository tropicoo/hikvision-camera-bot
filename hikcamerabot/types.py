from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from hikcamerabot.handlers.event_task import AbstractTaskEvent  # noqa
    from hikcamerabot.services.abstract import AbstractService  # noqa
    from hikcamerabot.services.alarm import AlarmService  # noqa
    from hikcamerabot.services.livestream import AbstractStreamService  # noqa

DispatchTypeDict = dict[str, Union['AbstractTaskEvent',
                                   'AbstractResultEventHandler']]
ServiceTypeType = Union[
    'AbstractStreamService',
    'AbstractService',
    'AlarmService',
]
