# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2024/10/6
"""
__all__ = ['CrankshaftComponent']

from dataclasses import dataclass

from ._component import Component


@dataclass
class CrankshaftComponent(Component):
    """曲轴组件"""
    crank_radius: float = 0.1  # 曲柄半径 [m]
    rod_length: float = 0.2  # 连杆长度 [m]
    speed: float = 20  # 转速 [r/s]

    @property
    def crank_rod_ratio(self):
        """曲柄连杆比"""
        return self.crank_radius / self.rod_length
