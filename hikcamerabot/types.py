from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from hikcamerabot.event_engine.handlers.inbound import AbstractTaskEvent  # noqa
    from hikcamerabot.services.abstract import AbstractService  # noqa
    from hikcamerabot.services.alarm import AlarmService  # noqa
    from hikcamerabot.services.livestream import AbstractStreamService  # noqa

DispatchTypeDict = dict[str, Union['AbstractTaskEvent', 'AbstractResultEventHandler']]
ServiceTypeType = Union[
    'AbstractStreamService',
    'AbstractService',
    'AlarmService',
]
