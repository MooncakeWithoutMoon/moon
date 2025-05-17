# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2024/10/6
"""
__all__ = ['EnvironmentComponent']

from dataclasses import dataclass, field

from cantera import one_atm

from ._component import Component


@dataclass
class EnvironmentComponent(Component):
    """环境组件"""
    temperature: float = 300  # 温度 [K]
    pressure: float = one_atm  # 压力 [Pa]
    species: dict[str, float] | list[float] = field(default_factory=lambda: {'N2': 0.79, 'O2': 0.21})  # 组分
