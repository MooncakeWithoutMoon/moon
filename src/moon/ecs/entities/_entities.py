# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2025/4/26
"""
__all__ = ['Entity', 'CylinderEntity', 'ValveEntity', 'CrankshaftEntity',
           'EnvironmentEntity', 'WorkingGroupEntity', 'EngineEntity']

import esper

from ..components import *


class HierarchyError(Exception):
    """父子关系错误"""
    pass


class Entity:
    _entities_registry = {}  # 实体ID到对象的映射

    def __init__(self):
        self._id = esper.create_entity()
        self._hierarchy = HierarchyComponent()  # 添加父子关系组件
        esper.add_component(self._id, self._hierarchy)
        Entity._entities_registry[self._id] = self  # 注册实例

    def __del__(self):
        self.delete()

    def __setattr__(self, name, value):
        # 自动添加组件到esper
        if isinstance(value, Component):
            self.add_components(value)
        super().__setattr__(name, value)

    def add_child(self, *child: 'Entity'):
        """添加子实体"""
        for each in child:
            if each.id == self._id:
                raise HierarchyError("不能添加自己为自己的子实体")
            if self._is_ancestor(each):
                raise HierarchyError("检测到循环依赖")
            # 如果子实体已有父实体，从原父实体中移除
            if each.parent is not None:
                original_parent = each.parent
                original_parent.remove_child(each)
            # 添加新的父子关系
            if each.id not in self._hierarchy.children:
                self._hierarchy.children.append(each.id)
                each._hierarchy.parent = self._id

    def remove_child(self, *child: 'Entity'):
        """移除子实体"""
        for each in child:
            if each.id not in self._hierarchy.children:
                raise ValueError("没有该子实体")
            self._hierarchy.children.remove(each.id)
            each._hierarchy.parent = None  # 清除子实体的父引用

    def add_components(self, *components: Component):
        """添加组件"""
        esper.add_component(self._id, *components)

    def _is_ancestor(self, entity: 'Entity') -> bool:
        """检查祖先关系"""
        parent_id = self._hierarchy.parent
        while True:
            if parent_id is None:
                return False
            if parent_id == entity.id:
                return True
            parent_id = esper.component_for_entity(parent_id, HierarchyComponent).parent

    @classmethod
    def get_entity(cls, entity_id: int) -> 'Entity':
        """通过id查找实体类"""
        try:
            return cls._entities_registry[entity_id]
        except KeyError:
            raise ValueError("没有该id的实体")

    @property
    def id(self) -> int:
        return self._id

    @property
    def parent(self) -> 'Entity':
        parent_id = self._hierarchy.parent
        return Entity._entities_registry.get(parent_id)

    @property
    def children(self) -> list['Entity']:
        return [Entity._entities_registry[cid]
                for cid in self._hierarchy.children
                if cid in Entity._entities_registry]

    def delete(self):
        """删除实体并清理注册表"""
        esper.delete_entity(self._id)
        del Entity._entities_registry[self._id]


class CylinderEntity(Entity):
    """气缸实体"""

    def __init__(self, crankshaft: 'CrankshaftEntity',
                 combustion_model: str = 'zero dimension',
                 heat_transfer_model: str = 'zero dimension'):
        super().__init__()
        self.reaction_mechanism = ReactionMechanismComponent()
        self.geometry = CylindricalCylinderGeometryComponent(crankshaft_id=crankshaft.id)
        match combustion_model:
            case 'zero dimension':
                self.combustion_model = ZeroDimensionCombustionModelComponent()
            case 'fractal turbulent':
                self.combustion_model = FractalTurbulentCombustionModelComponent()
            case _:
                raise ValueError("combustion_model can only be 'zero dimension', "
                                 "'fractal turbulent'")

        match heat_transfer_model:
            case 'woschni':
                self.heat_transfer_model = WoschniHeatTransferComponent()
            case 'hohenberg':
                self.heat_transfer_model = HohenbergHeatTransferComponent()
            case 'eichelberg':
                self.heat_transfer_model = EichelbergHeatTransferComponent()
            case 'sitkel':
                self.heat_transfer_model = SitkelHeatTransferComponent()
            case _:
                raise ValueError("heat_transfer_model can only be 'woschni', "
                                 "'hohenberg', 'eichelberg', 'sitkel'")


class CrankshaftEntity(Entity):
    """曲轴实体"""

    def __init__(self):
        super().__init__()
        self.crankshaft = CrankshaftComponent()


class ValveEntity(Entity):
    """阀门实体"""

    def __init__(self, upstream: Entity, downstream: Entity):
        super().__init__()
        self.valve = ValveComponent(upstream_id=upstream.id, downstream_id=downstream.id)


class SparkPlugEntity(Entity):
    """火花塞实体"""

    def __init__(self, cylinder: Entity):
        super().__init__()
        self.spark_plug = SparkPlugComponent(cylinder_id=cylinder.id)


class EnvironmentEntity(Entity):
    """环境实体"""

    def __init__(self):
        super().__init__()
        self.environment = EnvironmentComponent()


class WorkingGroupEntity(Entity):
    """工作组实体"""

    def __init__(self, *children):
        super().__init__()
        self.reaction_mechanism = ReactionMechanismComponent()
        self.add_child(*children)


class EngineEntity(Entity):
    """发动机实体"""
