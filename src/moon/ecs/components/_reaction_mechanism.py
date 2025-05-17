# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2025/4/26
"""
__all__ = ['ReactionMechanismComponent']

from dataclasses import dataclass

from ._component import Component
from ...reaction_mechanism import *


@dataclass
class ReactionMechanismComponent(Component):
    """化学反应机理组件"""
    reaction_mechanism = GRIMesh30  # 反应机理
