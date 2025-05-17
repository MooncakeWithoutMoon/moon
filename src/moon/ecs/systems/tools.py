# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2025/4/26
"""
from typing import Callable

import esper
from numpy import pi, remainder

from ..components import *


def get_reaction_mechanism(entity_id: int) -> str:
    """寻找反应机理, 查找顺序为本身、同级实体、父级实体, 如果未找到则引发ValueError"""
    # 首先查找自己是否有反应机理组件
    try:
        return esper.component_for_entity(entity_id, ReactionMechanismComponent).reaction_mechanism
    except KeyError:
        pass
    # 然后查找自己同级的实体是否有反应机理组件
    parent_id = esper.component_for_entity(entity_id, HierarchyComponent).parent
    if parent_id is None:
        # 如果没有父组件则返回None
        raise ValueError('缺少反应机理！')
    children_id = esper.component_for_entity(parent_id, HierarchyComponent).children
    for each in children_id:
        try:
            return esper.component_for_entity(each, ReactionMechanismComponent).reaction_mechanism
        except KeyError:
            pass
    # 再次查找父级实体是否有反应机理组件
    try:
        return esper.component_for_entity(parent_id, ReactionMechanismComponent).reaction_mechanism
    except KeyError:
        # 未找到则返回None
        raise ValueError('缺少反应机理！')


def change_time_func(speed, origin_time_func: Callable[[float], float]) -> Callable[[float], float]:
    """将原本关于曲轴转角的函数转化为关于时间的函数"""

    def time_func(time: float) -> float:
        angle = remainder(time * speed * 2 * pi, 4 * pi)
        return origin_time_func(angle)

    return time_func

def get_speed(entity_id: int) -> float:
    """获取当前所在工作组的转速, 如果当前工作组包含多个曲轴或没有曲轴则会引发ValueError"""
    parent = esper.component_for_entity(entity_id, HierarchyComponent).parent
    children = esper.component_for_entity(parent, HierarchyComponent).children
    crank = []
    for each in children:
        try:
            crank_component = esper.component_for_entity(each, CrankshaftComponent)
            crank.append(crank_component)
        except KeyError:
            pass
    if len(crank) == 0:
        raise ValueError('工作组缺少曲轴')
    if len(crank) > 1:
        raise ValueError('工作组包含多个曲轴')
    return crank[0].speed
