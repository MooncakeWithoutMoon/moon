# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2024/10/6
"""
__all__ = ['SparkPlugComponent', 'OffsetSparkPlug']

from dataclasses import dataclass
from typing import Callable

from numpy import deg2rad

from ._component import Component


@dataclass
class SparkPlugComponent(Component):
    """中心火花塞组件"""
    cylinder_id: int = None  # 气缸实体id
    ignition_energy: float = 1e-3  # 点火能量 [J]
    electrode_spacing: float = 1e-3  # 电极间距 [m]
    ignition_start: float = deg2rad(350)   # 点火起始角度 [rad]
    ignition_end: float = deg2rad(351)  # 点火结束角 [rad]
    time_function: Callable[[float], float] = None  # 时间函数 (点火规律)


@dataclass
class OffsetSparkPlug(Component):
    """偏置火花塞组件"""
    raise NotImplementedError
