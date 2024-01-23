#!/usr/bin/env python3
"""Use redis for basic operations"""
import uuid
from functools import wraps
from typing import Union, Callable

import redis


def count_calls(method: Callable) -> Callable:
    """increments the count for that key every time the method is called and
       returns the value returned by the original method
    """
    key = method.__qualname__

    @wraps(method)
    def wrapper(self, *args, **kwds):
        """wrapper function"""
        self._redis.incr(key)
        return method(self, *args, **kwds)

    return wrapper


def call_history(method: Callable) -> Callable:
    """decorator to store the history of inputs and outputs
       for a particular function
    """

    @wraps(method)
    def wrapper(self, *args, **kwds):
        """wrapper function"""
        self._redis.rpush(method.__qualname__ + ":inputs", str(args))
        output = str(method(self, *args, **kwds))
        self._redis.rpush(method.__qualname__ + ":outputs", output)
        return output

    return wrapper


def replay(fn: Callable):
    """display the history of calls of a particular function"""
    rds = redis.Redis()
    func_name = fn.__qualname__
    input = rds.lrange("{}:inputs".format(func_name), 0, -1)
    output = rds.lrange("{}:outputs".format(func_name), 0, -1)
    print('{} was called {} times:'.format(func_name, int(rds.get(func_name))))
    for k, v in zip(input, output):
        print('{}(*{}) -> {}'.format(func_name,
                                     k.decode('utf-8'), v.decode('utf-8')))


class Cache:
    """Cache class"""

    def __init__(self):
        """store an instance of the Redis client as a private variable"""
        self._redis = redis.Redis()
        self._redis.flushdb()

    @count_calls
    @call_history
    def store(self, data: Union[str, bytes, int, float]) -> str:
        """generate a random key (e.g. using uuid), store the input data
           in Redis using the random key and return the key
        """
        key = str(uuid.uuid4())
        self._redis.set(key, data)
        return key

    def get(self, key: str, fn: Callable) -> Union[str, bytes, int, float]:
        """convert the data back to the desired format"""
        value = self._redis.get(key)
        if fn:
            value = fn(value)
        return value

    def get_str(self, key: str) -> str:
        """parametrize Cache.get"""
        return self.get(key, lambda x: x.decode('utf-8'))

    def get_int(self, key: str) -> int:
        """parametrize Cache.get"""
        return self.get(key, int)
