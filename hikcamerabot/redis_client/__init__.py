import pickle

import redis
import ujson


class RedisClient:
    def __init__(self, log):
        self._log = log
        self._redis = redis.StrictRedis(host='localhost', port=6379)

    def send(self, key, pickle_dump=False, **kwargs):
        if pickle_dump:
            self._log.debug(kwargs)
            self._log.debug(kwargs)
            self._log.debug(kwargs)
        kwargs = pickle.dumps(kwargs) if pickle_dump else ujson.dumps(kwargs)
        self._redis.lpush(key, kwargs)

    def get_data(self, key):
        data = self._redis.rpop(key)
        try:
            return pickle.loads(data)
        except pickle.UnpicklingError:
            self._log.debug(data)
            return ujson.loads(data)
        except TypeError:
            pass
