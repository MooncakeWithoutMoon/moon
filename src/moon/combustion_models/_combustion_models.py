# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2025/4/26
"""
__all__ = ["ZeroDimensional", "SITwoZoneGeometry"]

from typing import Callable, Any

from cantera import IdealGasReactor, Solution, Wall, Reservoir, MassFlowController
from numpy import pi, exp, sqrt

from ..geometry import *
from ..heat_transfer import *


class ZeroDimensional:
    """零维模型"""

    def __init__(self,
                 reaction_mechanism: str,
                 geometry: EngineGeometry,
                 heat_transfer: str | None = 'hohenberg',
                 combustion_chamber_type: str | None = None,
                 cover_temperature: float | None = 400,
                 wall_temperature: float | None = 400,
                 crown_temperature: float | None = 500):
        self._reaction_mechanism = reaction_mechanism  # 反应机理
        self._geometry = geometry  # 发动机几何
        self._heat_transfer = heat_transfer  # 传热模型
        self._combustion_chamber_type = combustion_chamber_type  # 燃烧室类别
        self._cover_temperature = cover_temperature  # 气缸盖温度 [K]
        self._wall_temperature = wall_temperature  # 缸套温度 [K]
        self._crown_temperature = crown_temperature  # 活塞冠温度 [K]

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
            match self._heat_transfer:
                case 'hohenberg':
                    heat_transfer_model = Hohenberg(cylinder, self._geometry)
                case 'eichelberg':
                    heat_transfer_model = Eichelberg(cylinder, self._geometry)
                case 'sitkel':
                    heat_transfer_model = Sitkel(cylinder, self._geometry, self._combustion_chamber_type)
                case _:
                    raise ValueError("heat_transfer must be 'hohenberg', 'eichelberg' or 'sitkel'")

            def heat_flux(time: float) -> float:
                """热流量"""
                coeff = heat_transfer_model.heat_transfer_coeff(time)
                area_cover = self._geometry.area_bore
                area_wall = self._geometry.piston_position(time) * self._geometry.bore * pi
                area_crown = area_cover * 1.3
                t = cylinder.thermo.T
                heat_flux_ = ((t - self._cover_temperature) * area_cover +
                              (t - self._wall_temperature) * area_wall +
                              (t - self._crown_temperature) * area_crown) * coeff
                return heat_flux_ / area_cover

            piston.heat_flux = heat_flux
            result["heat transfer"] = piston
            return result


class FractalTurbulent:
    """分形湍流燃烧模型"""

    def __init__(self,
                 reaction_mechanism: str,
                 geometry: SITwoZoneGeometry,
                 ignition_time_function: Callable[[float], float],
                 flame_speed: Callable[[IdealGasReactor], Callable[[float], float]],
                 fire_core_volume_fraction: float = 0.001,
                 end_volume_fraction: float = 0.001,
                 u_rms_0: float = 4,
                 reference_flame_radius: float = 0.006,
                 reference_engine_speed: float = 1000 / 60,
                 heat_transfer: str | None = 'hohenberg',
                 combustion_chamber_type: str | None = None,
                 cover_temperature: float | None = 400,
                 wall_temperature: float | None = 400,
                 crown_temperature: float | None = 500):
        self._reaction_mechanism = reaction_mechanism  # 反应机理
        self._geometry = geometry  # 发动机几何
        self._fire_core_volume_fraction = fire_core_volume_fraction  # 初始火核体积百分比
        self._end_volume_fraction = end_volume_fraction  # 结束时未燃区体积百分比
        self._ignition_time_function = ignition_time_function  # 点火时间函数
        self._flame_speed = flame_speed  # 火焰速度计算函数
        self._u_rms_0 = u_rms_0  # 初始均方根湍流速度
        self._reference_flame_radius = reference_flame_radius  # 参考火焰半径 [m]
        self._reference_engine_speed = reference_engine_speed  # 参考转速 [r/s]
        self._heat_transfer = heat_transfer  # 传热模型
        self._combustion_chamber_type = combustion_chamber_type  # 燃烧室类别
        self._cover_temperature = cover_temperature  # 气缸盖温度
        self._wall_temperature = wall_temperature  # 缸套温度
        self._crown_temperature = crown_temperature  # 活塞冠温度

        # 与分形湍流燃烧模型有关的参数
        self._tau = 0  # 特征时间尺度 [s]
        self._m_u_tr = 0  # 壁面燃烧切换时刻的未燃区质量 [kg]
        self._is_tr = False  # 是否开始分形与壁面燃烧切换

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
        burning_rate.mass_flow_rate = self._fractal_combustion_model(burned, unburned)
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
            match self._heat_transfer:
                case 'hohenberg':
                    burned_heat_transfer = Hohenberg(burned, self._geometry)
                    unburned_heat_transfer = Hohenberg(unburned, self._geometry)
                case 'eichelberg':
                    burned_heat_transfer = Eichelberg(burned, self._geometry)
                    unburned_heat_transfer = Eichelberg(unburned, self._geometry)
                case 'sitkel':
                    burned_heat_transfer = Sitkel(burned, self._geometry, self._combustion_chamber_type)
                    unburned_heat_transfer = Sitkel(unburned, self._geometry, self._combustion_chamber_type)
                case _:
                    raise ValueError("heat_transfer must be 'hohenberg', 'eichelberg' or 'sitkel'")

            def burned_heat_flux(time: float) -> float:
                """已燃区热流量"""
                alpha = burned_heat_transfer.heat_transfer_coeff(time)
                burned_volume_percentage = burned.volume / self._geometry.cylinder_volume(time)
                a_cover = self._geometry.burned_cover_area(time, burned_volume_percentage)
                a_wall = self._geometry.burned_wall_area(time, burned_volume_percentage)
                a_crown = self._geometry.burned_piston_area(time, burned_volume_percentage)
                t = burned.T
                return (((t - self._crown_temperature) * a_cover +
                         (t - self._wall_temperature) * a_wall +
                         (t - self._crown_temperature) * a_crown) * alpha)

            area_bore = self._geometry.area_bore

            def unburned_heat_flux(time: float) -> float:
                """未燃区热流量, 认为全从活塞面积流出"""
                alpha = unburned_heat_transfer.heat_transfer_coeff(time)
                burned_volume_percentage = burned.volume / self._geometry.cylinder_volume(time)
                a_cover = self._geometry.unburned_cover_area(time, burned_volume_percentage)
                a_wall = self._geometry.unburned_wall_area(time, burned_volume_percentage)
                a_crown = self._geometry.unburned_piston_area(time, burned_volume_percentage)
                t = unburned.T
                return (((t - self._cover_temperature) * a_cover +
                         (t - self._wall_temperature) * a_wall +
                         (t - self._crown_temperature) * a_crown) * alpha / area_bore)

            burned_heat = Wall(burned, environment)
            burned_heat.heat_flux = burned_heat_flux  # 已燃区传热
            piston.heat_flux = unburned_heat_flux  # 未燃区传热
            result["burned heat transfer"] = burned_heat
            result["unburned heat transfer"] = piston
            return result

    def _fractal_combustion_model(self, burned: IdealGasReactor,
                                  unburned: IdealGasReactor) -> Callable[[float], float]:
        """
        分形湍流燃烧模型
        :param burned: 已燃区反应器
        :param unburned: 未燃区反应器
        :return: 燃烧速率计算函数, 输入为仿真时间 [s], 输出为质量燃烧速率 [kg/s]
        """
        rho_u0 = unburned.thermo.density_mass  # 初始密度
        bore = self._geometry.bore  # 缸径
        flame_speed = self._flame_speed(unburned)  # 火焰速度计算函数
        self._tau = 0  # 特征时间尺度 [s]
        self._m_u_tr = 0  # 壁面燃烧切换时刻的未燃区质量 [kg]
        self._is_tr = False  # 是否开始分形与壁面燃烧切换

        def burning_rate(time: float) -> float:
            h_gap = self._geometry.piston_position(time)  # 活塞顶端到气缸盖距离
            volume = self._geometry.cylinder_volume(time)  # 气缸体积
            # 当未燃区小于设置的停止体积时，认为已燃烧完全
            if unburned.volume < volume * self._end_volume_fraction:
                return 0
            else:
                burned_volume_percentage = burned.volume / volume  # 已燃区体积百分比
                a_f = self._geometry.flame_area(time, burned_volume_percentage)  # 火焰面积
                r_f = self._geometry.flame_radius(time, burned_volume_percentage)  # 火焰半径
                s_l = flame_speed(time)  # 未拉伸火焰速度
                rho_u = unburned.thermo.density_mass  # 未燃区密度
                u_rms_0 = self._u_rms_0  # 初始均方根湍流速度
                u_rms = u_rms_0 * (rho_u0 / rho_u) ** (1 / 3)  # 均方根湍流速度
                l_i = min(r_f, 0.5 * bore, h_gap)  # 积分尺度
                epsilon = u_rms ** 3 / l_i  # 湍流耗散率
                nu = unburned.thermo.viscosity / rho_u  # 未燃区运动粘度
                k_s = sqrt(epsilon / nu) / 3.55 ** (2 / 3)  # 火焰拉伸系数
                k_e = 0  # 火焰拉伸系数
                u_l = s_l * (1 - nu / s_l ** 2 * (k_e + k_s))  # 拉伸的火焰速度
                ll = l_i / (nu ** 3 / epsilon) ** 0.25  # 火焰褶皱尺度比
                omiga_wr = (r_f / self._reference_flame_radius * self._geometry.speed /
                            self._reference_engine_speed)  # 无量纲火焰褶皱率
                w1 = 1 - exp(-omiga_wr)  # 点火修正权重系数
                d3_min = 2.05  # 最小分形维数
                d3_max = d3_min * (1 - w1) + 2.35 * w1  # 最大分形维数
                d3 = (d3_max * u_rms + d3_min * s_l) / (u_rms + s_l)  # 分形维数
                m_b_dot = rho_u * a_f * u_l * ll ** (d3 - 2)  # 燃烧速率(未经近壁燃烧加权)
                # 判断是否达到壁面燃烧条件
                if (r_f + l_i / 2 >= bore / 2) and (self._is_tr is False):
                    self._m_u_tr = unburned.mass  # 参考质量
                    self._tau = self._m_u_tr / m_b_dot  # 时间常数
                    self._is_tr = True
                # 计算壁面燃烧修正
                if self._is_tr is True:
                    mass_u = unburned.mass  # 未燃区质量
                    w2 = 1 - mass_u / self._m_u_tr  # 近壁修正权重系数
                    return (1 - w2) * m_b_dot + w2 * (mass_u / self._tau)
                # 未达到近壁燃烧条件则返回原始燃烧速率
                else:
                    return m_b_dot

        return burning_rate
