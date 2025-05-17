# -*- coding:utf-8 -*-
"""
提供发动机性能计算工具
@Author: MoonCake Without Moon
@Time: 2025/2/18
"""
__all__ = [
    'indicated_power', 'mean_indicated_power', 'indicated_torque', 'mean_indicated_torque', 'imep'
]

from numpy import array, sin, cos, sqrt, pi, remainder, max, min
from scipy.integrate import simpson


def indicated_power(pressure: float, time: float, speed: float,
                    bore: float, stroke: float, lambda_: float) -> float:
    """
    瞬时指示功率 [W]
    :param pressure: 压力 [Pa]
    :param time: 压力对应的时间 [s]
    :param speed: 发动机转速 [r/s]
    :param bore: 缸径 [m]
    :param stroke: 冲程 [m]
    :param lambda_: 曲柄连杆比
    :return: 瞬时指示功率 [W]
    """

    def piston_velocity(t: float) -> float:
        """
        活塞速度
        :param t: 时间 [s]
        :return: 活塞速度 (向下为正) [m/s]
        """
        angle = remainder(2 * pi * speed * t, 4 * pi)
        return stroke * (lambda_ * sin(angle) * cos(angle) / sqrt(lambda_ ** 2 * sin(angle) ** 2 + 1)
                         + sin(angle)) * pi * speed

    area = 0.25 * pi * bore ** 2  # 气缸圆面积 [m**2]
    return pressure * area * piston_velocity(time)


def mean_indicated_power(pressures: array, times: array, speed: float,
                         bore: float, stroke: float, lambda_: float) -> float:
    """
    平均指示功率 [W]
    :param pressures: 压力 [Pa]
    :param times: 压力对应的时间 [s]
    :param speed: 发动机转速 [r/s]
    :param bore: 缸径 [m]
    :param stroke: 冲程 [m]
    :param lambda_: 曲柄连杆比
    :return: 平均指示功率 [W]
    """
    powers = indicated_power(pressures, times, speed, bore, stroke, lambda_)
    return simpson(y=powers, x=times) / (max(times) - min(times))


def imep(pressures: array, times: array, speed: float,
         bore: float, stroke: float, lambda_: float) -> float:
    """
    平均指示压力 [Pa]
    :param pressures: 压力 [Pa]
    :param times: 压力对应的时间 [s]
    :param speed: 发动机转速 [r/s]
    :param bore: 缸径 [m]
    :param stroke: 冲程 [m]
    :param lambda_: 曲柄连杆比
    :return: 平均指示压力 [Pa]
    """
    return mean_indicated_power(pressures, times, speed, bore, stroke, lambda_) * (
            max(times) - min(times)) / (
            0.25 * pi * bore ** 2 * stroke)


def indicated_torque(pressure: float, time: float, speed: float,
                     bore: float, stroke: float, lambda_: float) -> float:
    """
    瞬时指示扭矩 [N*m]
    :param pressure: 压力 [Pa]
    :param time: 压力对应的时间 [s]
    :param speed: 发动机转速 [r/s]
    :param bore: 缸径 [m]
    :param stroke: 冲程 [m]
    :param lambda_: 曲柄连杆比
    :return: 瞬时指示扭矩 [N*m]
    """
    angular_speed = speed * 2 * pi  # 角速度 [rad/s]
    return indicated_power(pressure, time, speed, bore, stroke, lambda_) / angular_speed


def mean_indicated_torque(pressures: array, times: array, speed: float,
                          bore: float, stroke: float, lambda_: float) -> float:
    """
    平均指示扭矩 [N*m]
    :param pressures: 压力 [Pa]
    :param times: 压力对应的时间 [s]
    :param speed: 发动机转速 [r/s]
    :param bore: 缸径 [m]
    :param stroke: 冲程 [m]
    :param lambda_: 曲柄连杆比
    :return: 平均指示扭矩 [N*m]
    """
    torques = indicated_torque(pressures, times, speed, bore, stroke, lambda_)
    return simpson(y=torques, x=times) / (max(times) - min(times))
