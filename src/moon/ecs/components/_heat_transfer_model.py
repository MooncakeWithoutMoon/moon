# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2025/4/8
"""
__all__ = ['WoschniHeatTransferComponent', 'HohenbergHeatTransferComponent',
           'EichelbergHeatTransferComponent', 'SitkelHeatTransferComponent']

from dataclasses import dataclass

from ._component import Component


@dataclass
class HeatTransferBase(Component):
    """传热基类"""
    cover_temperature: float = 400  # 缸盖温度 [K]
    wall_temperature: float = 400  # 缸壁温度 [K]
    crown_temperature: float = 500  # 活塞冠温度 [K]


@dataclass
class WoschniHeatTransferComponent(HeatTransferBase):
    """Woschni 传热组件"""
    combustion_chamber_type: str = 'direct injection'  # 燃烧室类别


@dataclass
class HohenbergHeatTransferComponent(HeatTransferBase):
    """Hohenberg 传热组件"""
    pass


@dataclass
class EichelbergHeatTransferComponent(HeatTransferBase):
    """Eichelberg 传热组件"""
    pass


@dataclass
class SitkelHeatTransferComponent(HeatTransferBase):
    """Sitkel 传热组件"""
    combustion_chamber_type: str = 'direct injection'  # 燃烧室类别
