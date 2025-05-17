# -*- coding:utf-8 -*-
"""
提供一些装饰器
@Author: MoonCake Without Moon
@Time: 2025/1/20
"""
__all__ = ['add_log', 'rad_to_time', 'deg_to_time']

from functools import wraps
from loguru import logger
from typing import Callable

from numpy import remainder, pi


def add_log(start_log: str | None = None, end_log: str | None = None):
    """
    用于添加日志信息的装饰器
    :param start_log: 开头的日志信息
    :param end_log: 结尾的日志信息
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if start_log is not None:
                logger.info(start_log)
            result = func(*args, **kwargs)
            if end_log is not None:
                logger.info(end_log)
            return result

        return wrapper

    return decorator


def rad_to_time(speed: float):
    """
    用于将关于曲轴转角的时间函数转化为关于时间的时间函数
    :param speed: 转速 [r/s]
    """

    def decorator(func: Callable[[float], float]):
        @wraps(func)
        def wrapper(time: float) -> float:
            rad = remainder(time * speed * 2 * pi, 4 * pi)
            return func(rad)

        return wrapper

    return decorator


def deg_to_time(speed: float):
    """
    用于将关于曲轴转角的时间函数转化为关于时间的时间函数
    :param speed: 转速 [r/s]
    """

    def decorator(func: Callable[[float], float]):
        @wraps(func)
        def wrapper(time: float) -> float:
            deg = remainder(time * speed * 360, 720)
            return func(deg)

        return wrapper

    return decorator
