# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2025/4/26
"""
__all__ = ["ZeroDimensional", "TwoZoneModel"]

from typing import Callable, Any

from cantera import IdealGasReactor, Solution, Wall, Reservoir, MassFlowController
from numpy import pi

from ..geometry import *
from ..heat_transfer import *
from .entrain_rate import *


class ZeroDimensional:
    """零维模型"""

    def __init__(self,
                 reaction_mechanism: str,
                 geometry: EngineGeometry,
                 heat_transfer: HeatTransferBase | None = None):
        self._reaction_mechanism = reaction_mechanism  # 反应机理
        self._geometry = geometry  # 发动机几何
        self._heat_transfer = heat_transfer  # 传热模型

    def build(self, init_tpx: tuple[float, float, dict[str, float] | list],
              init_volume: float) -> dict[str, Any]:
        """
        零维模型
        :param init_tpx: 初始温度、压力、组分
        :param init_volume: 初始体积
        :return: 包含了反应器网络各组件的字典
            "cylinder": 气缸反应器 Cantera IdealGasReactor
            "piston": 活塞 Cantera Wall
            "environment": 外界环境 Cantera Reservoir
            "heat transfer": 传热 Cantera Wall, 如果 heat_transfer 设置为 None 则为 None
            "reactors": 所有反应器组成的列表
        """
        gas = Solution(self._reaction_mechanism)
        gas.TPX = init_tpx
        # 气缸
        cylinder = IdealGasReactor(gas)
        cylinder.volume = init_volume
        # 外界环境
        gas.TPX = 300, 101325, {'N2': 0.79, 'O2': 0.21}
        environment = Reservoir(gas)
        # 活塞
        piston = Wall(cylinder, environment)
        piston.area = self._geometry.area_bore
        piston.velocity = self._geometry.piston_velocity
        # 如果没有传热则返回结果
        result = {
            "cylinder": cylinder,
            "piston": piston,
            "environment": environment,
            "heat transfer": None,
            "reactors": [cylinder]
        }
        if self._heat_transfer is None:
            return result
        # 如果有传热则加上传热
        else:
            heat_transfer_model = self._heat_transfer.heat_transfer_coefficient(cylinder, self._geometry)

            def heat_flux(time: float) -> float:
                """热流量"""
                alpha = heat_transfer_model(time)  # 传热系数
                area_cover = self._geometry.area_bore
                area_wall = self._geometry.piston_position(time) * self._geometry.bore * pi
                area_crown = area_cover * 1.3
                t = cylinder.thermo.T
                heat_flux_ = ((t - self._heat_transfer.cover_temperature) * area_cover +
                              (t - self._heat_transfer.wall_temperature) * area_wall +
                              (t - self._heat_transfer.crown_temperature) * area_crown) * alpha
                return heat_flux_ / area_cover

            piston.heat_flux = heat_flux
            result["heat transfer"] = piston
            return result


class TwoZoneModel:
    """双区模型"""

    def __init__(self,
                 reaction_mechanism: str,
                 geometry: SITwoZoneGeometry,
                 ignition_time_function: Callable[[float], float],
                 entrain_rate: EntrainRateBase,
                 heat_transfer: HeatTransferBase | None = None,
                 fire_core_volume_fraction: float = 0.001):
        self._reaction_mechanism = reaction_mechanism  # 反应机理
        self._geometry = geometry  # 发动机几何
        self._ignition_time_function = ignition_time_function  # 点火时间函数
        self._entrain_rate = entrain_rate  # 卷吸模型
        self._heat_transfer = heat_transfer  # 传热模型
        self._fire_core_volume_fraction = fire_core_volume_fraction  # 初始火核体积百分比

    def build_ignition(self, init_tpx: tuple[float, float, dict[str, float] | list],
                       init_volume: float) -> dict[str, Any]:
        """
        点火阶段的反应器网络
        :param init_tpx: 初始温度、压力、组分
        :param init_volume: 初始体积
        :return: 包含了反应器网络各组件的字典
            "spark plug": 火花塞 Cantera Wall
            其余字段见 self.build_combustion() 函数文档
        """
        result = self.build_combustion(
            burned_tpx=init_tpx,
            burned_volume=init_volume * self._fire_core_volume_fraction,
            unburned_tpx=init_tpx,
            unburned_volume=init_volume * (1 - self._fire_core_volume_fraction)
        )
        # 添加火花塞
        spark_plug = Wall(result["environment"], result["burned"])
        spark_plug.heat_flux = self._ignition_time_function
        result["spark plug"] = spark_plug
        return result

    def build_combustion(self, burned_tpx: tuple[float, float, dict[str, float] | list],
                         burned_volume: float,
                         unburned_tpx: tuple[float, float, dict[str, float] | list],
                         unburned_volume: float) -> dict[str, Any]:
        """
        燃烧阶段的反应器网络
        :param burned_tpx: 已燃区初始温度、压力、组分
        :param burned_volume: 已燃区初始体积
        :param unburned_tpx: 未燃区初始温度、压力、组分
        :param unburned_volume: 未燃区初始体积
        :return: 包含了反应器网络各组件的字典
            "burned zone": 已燃区反应器 Cantera IdealGasReactor
            "unburned zone": 未燃区反应器 Cantera IdealGasReactor
            "piston": 活塞 Cantera Wall
            "environment": 外界环境 Cantera Reservoir
            "burning rate": 燃烧速率，即已燃区中气体进入未燃区速度 Cantera MassFlowController
            "flame front": 火焰前锋 Cantera Wall
            "burned heat transfer": 已燃区传热 Cantera Wall
            "unburned heat transfer": 未燃区传热 Cantera Wall
            "reactors": 所有反应器组成的列表
        """
        gas = Solution(self._reaction_mechanism)
        # 已燃区
        gas.TPX = burned_tpx
        burned = IdealGasReactor(gas)
        burned.volume = burned_volume
        # 未燃区
        gas.TPX = unburned_tpx
        unburned = IdealGasReactor(gas)
        unburned.volume = unburned_volume
        # 外界环境
        gas.TPX = 300, 101325, {'O2': 0.21, 'N2': 0.79}
        environment = Reservoir(gas)
        # 活塞
        piston = Wall(unburned, environment)
        piston.area = self._geometry.area_bore
        piston.velocity = self._geometry.piston_velocity
        # 压力平衡
        flame_front = Wall(burned, unburned)
        flame_front.area = self._geometry.area_bore * 2
        flame_front.expansion_rate_coeff = unburned.thermo.sound_speed
        # 设置燃烧速率为分形湍流燃烧模型
        burning_rate = MassFlowController(unburned, burned)
        burning_rate.mass_flow_rate = self._entrain_rate.mass_flow_rate(burned, unburned)
        # 如果没有传热则返回结果
        result = {
            "burned zone": burned,
            "unburned zone": unburned,
            "piston": piston,
            "environment": environment,
            "burning rate": burning_rate,
            "flame front": flame_front,
            "burned heat transfer": None,
            "unburned heat transfer": None,
            "reactors": [burned, unburned]
        }
        if self._heat_transfer is None:
            return result
        # 如果有传热则加上传热
        else:
            burned_heat_transfer = self._heat_transfer.heat_transfer_coefficient(burned, self._geometry)
            unburned_heat_transfer = self._heat_transfer.heat_transfer_coefficient(unburned, self._geometry)

            def burned_heat_flux(time: float) -> float:
                """已燃区热流量"""
                alpha = burned_heat_transfer(time)
                burned_volume_percentage = burned.volume / self._geometry.cylinder_volume(time)
                a_cover = self._geometry.burned_cover_area(time, burned_volume_percentage)
                a_wall = self._geometry.burned_wall_area(time, burned_volume_percentage)
                a_crown = self._geometry.burned_piston_area(time, burned_volume_percentage)
                t = burned.T
                return (((t - self._heat_transfer.cover_temperature) * a_cover +
                         (t - self._heat_transfer.wall_temperature) * a_wall +
                         (t - self._heat_transfer.crown_temperature) * a_crown) * alpha)

            area_bore = self._geometry.area_bore

            def unburned_heat_flux(time: float) -> float:
                """未燃区热流量, 认为全从活塞面积流出"""
                alpha = unburned_heat_transfer(time)
                burned_volume_percentage = burned.volume / self._geometry.cylinder_volume(time)
                a_cover = self._geometry.unburned_cover_area(time, burned_volume_percentage)
                a_wall = self._geometry.unburned_wall_area(time, burned_volume_percentage)
                a_crown = self._geometry.unburned_piston_area(time, burned_volume_percentage)
                t = unburned.T
                return (((t - self._heat_transfer.cover_temperature) * a_cover +
                         (t - self._heat_transfer.wall_temperature) * a_wall +
                         (t - self._heat_transfer.crown_temperature) * a_crown) * alpha / area_bore)

            burned_heat = Wall(burned, environment)
            burned_heat.heat_flux = burned_heat_flux  # 已燃区传热
            piston.heat_flux = unburned_heat_flux  # 未燃区传热
            result["burned heat transfer"] = burned_heat
            result["unburned heat transfer"] = piston
            return result
