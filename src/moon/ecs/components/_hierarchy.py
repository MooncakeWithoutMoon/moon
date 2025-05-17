# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2025/4/26
"""
__all__ = ['HierarchyComponent']

from dataclasses import dataclass, field

from ._component import Component


@dataclass
class HierarchyComponent(Component):
    """父子关系组件"""
    parent: int | None = None  # 父实体ID
    children: list[int] = field(default_factory=list)  # 子实体ID列表
