# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2025/4/8
"""
from abc import ABC, abstractmethod

from cantera import Solution, IdealGasReactor, Wall, Reservoir

from .network_resource import ReactorNetworkResource
from .tools import *
from ..components import *
from ...geometry import *


class InitSystem(ABC):
    @abstractmethod
    def __init__(self, network_resource: ReactorNetworkResource):
        pass

    @abstractmethod
    def init(self) -> None:
        pass


class InitRegistry:
    """注册需初始化的类（单例模式）"""

    def __init__(self):
        self.registered_classes = []  # 用于存储注册的类
        self._levels = []  # 用于存储对应的等级

    def __call__(self, level: int = 1):
        if type(level) != int:
            raise TypeError('level must be int')
        if level < 0:
            raise ValueError("level cannot be negative")

        def decorator(cls: type):
            # 找到插入位置
            for i, existing_level in enumerate(self._levels):
                if existing_level > level:
                    insert_pos = i
                    break
            else:
                insert_pos = len(self._levels)
            # 同步插入等级和类
            self._levels.insert(insert_pos, level)
            self.registered_classes.insert(insert_pos, cls)
            return cls

        return decorator

    def init(self) -> None:
        for cls in self.registered_classes:
            cls._instance.init()


init_registry = InitRegistry()

reactor_level = 10  # 构建反应器的系统等级
heat_transfer_level = 20  # 构建传热模型的系统等级
flow_device_level = 30  # 构建流动装置的系统等级


@init_registry(level=reactor_level)
class ZeroDimensionalCombustionInitSystem(InitSystem):
    def __init__(self, network_resource: ReactorNetworkResource):
        self.network_resource = network_resource

    def init(self) -> None:
        for entity, (geo_component, combustion) in esper.get_components(
                CylindricalCylinderGeometryComponent, ZeroDimensionCombustionModelComponent):
            # 得到连接的曲轴组件
            try:
                crank = esper.component_for_entity(geo_component.crank_id, CrankshaftComponent)
            except KeyError:
                raise AttributeError('未指定曲轴！')

            # 气缸几何计算类
            geometry = EngineGeometry(
                speed=crank.speed, stroke=crank.crank_radius * 2, epsilon=geo_component.compression_ratio,
                bore=geo_component.bore, crank_rod_ratio=crank.crank_rod_ratio,
                tdc_gap=geo_component.tdc_gap
            )

            geo_component.geometry = geometry

            # 得到反应机理
            mechanism = get_reaction_mechanism(entity)
            gas = Solution(mechanism)
            gas.TPX = 300, 101325, {'N2': 0.79, 'O2': 0.21}
            cylinder = IdealGasReactor(gas)
            cylinder.volume = geometry.tdc_volume
            environment = Reservoir(gas)
            piston = Wall(cylinder, environment)
            piston.area = geometry.area_bore
            piston.velocity = geometry.piston_velocity

            combustion.reactor = cylinder
            self.network_resource.reactors[entity] = cylinder
