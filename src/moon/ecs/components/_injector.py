# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2025/4/8
"""
__all__ = ['PortFuelInjectorComponent', 'CylinderInjectorComponent']

from dataclasses import dataclass

from ._component import Component


@dataclass
class PortFuelInjectorComponent(Component):
    """进气道喷油器组件"""
    raise NotImplementedError


@dataclass
class CylinderInjectorComponent(Component):
    """气缸喷油器组件"""
    raise NotImplementedError
