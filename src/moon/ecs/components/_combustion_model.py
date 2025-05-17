# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2025/4/8
"""
__all__ = ['FractalTurbulentCombustionModelComponent', 'WiebeCombustionModelComponent',
           'ZeroDimensionCombustionModelComponent']

from dataclasses import dataclass

from cantera import IdealGasReactor

from ._component import Component


class EnginePerformance:
    """计算发动机性能"""

    def __init__(self, reactor: IdealGasReactor):
        self._reactor = reactor

    @property
    def temperature(self) -> float:
        """温度 [K]"""
        return self._reactor.thermo.T

    @property
    def pressure(self) -> float:
        """压力 [Pa]"""
        return self._reactor.thermo.P

    @property
    def species(self) -> list[float]:
        """组分"""
        return self._reactor.thermo.X


@dataclass
class FractalTurbulentCombustionModelComponent(Component):
    """分形湍流燃烧模型组件"""
    init_u_rms: float = 2.5  # 初始均方根湍流速度 [m/s]
    r_f_ref: float = 0.06  # 参考火焰半径 [m]
    n_ref: float = 1000 / 60  # 参考转速 [r/s]
    _burned_zone = None  # 已燃区
    _unburned_zone = None  # 未燃区

    @property
    def burned_zone(self):
        return self._burned_zone

    @burned_zone.setter
    def burned_zone(self, value):
        self._burned_zone = EnginePerformance(value)

    @property
    def unburned_zone(self):
        return self._unburned_zone

    @unburned_zone.setter
    def unburned_zone(self, value):
        self._unburned_zone = EnginePerformance(value)


@dataclass
class WiebeCombustionModelComponent(Component):
    """Wiebe 燃烧模型组件"""
    raise NotImplementedError


@dataclass
class ZeroDimensionCombustionModelComponent(Component):
    """零维燃烧模型组件"""
    raise NotImplementedError
