# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2024/10/6
"""
__all__ = ['ValveComponent']

from dataclasses import dataclass
from typing import Callable

from cantera import Valve

from ._component import Component


@dataclass
class ValveComponent(Component):
    """阀门组件"""
    open: float = 0  # 开启角 [rad]
    close: float = 0  # 关闭角 [rad]
    valve_coefficient: float = 1e-5  # 阀系数
    time_function: Callable[[float], float] = None  # 时间函数
    upstream_id: int = None  # 上游实体ID
    downstream_id: int = None  # 下游实体ID

    def __post_init__(self):
        self.valve: Valve | None = None  # cantera阀门

    @property
    def mass_flow_rate(self) -> float:
        """质量流量 [kg/s]"""
        if self.valve is None:
            return 0
        else:
            return self.valve.mass_flow_rate
