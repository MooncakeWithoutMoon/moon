# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2025/6/20
"""
__all__ = ['EntrainRateBase', 'Wiebe', 'FractalTurbulent']

from abc import ABC, abstractmethod
from typing import Callable

from cantera import IdealGasReactor
from numpy import exp, sqrt

from ..geometry import *


class EntrainRateBase(ABC):
    """卷吸速率基类"""

    @abstractmethod
    def mass_flow_rate(self, burned: IdealGasReactor,
                       unburned: IdealGasReactor) -> Callable[[float], float]:
        """
        从未燃区到已燃区的质量流率 [kg/s]
        :param burned: 已燃区
        :param unburned: 未燃区
        :return: 燃烧速率计算函数, 输入为仿真时间 [s], 输出为质量燃烧速率 [kg/s]
        """
        pass


class Wiebe(EntrainRateBase):
    """Wiebe燃烧模型"""

    def _wiebe_function(self, start: float, end: float, m: float) -> Callable[[float], float]:
        """
        Wiebe函数
        :param start: 起始点
        :param end: 终止点
        :param m: 品质指数
        :return: Wiebe函数
        """
        raise NotImplementedError

    def mass_flow_rate(self, burned: IdealGasReactor,
                       unburned: IdealGasReactor) -> Callable[[float], float]:
        """
        从未燃区到已燃区的质量流率 [kg/s]
        :param burned: 已燃区
        :param unburned: 未燃区
        :return: 燃烧速率计算函数, 输入为仿真时间 [s], 输出为质量燃烧速率 [kg/s]
        """
        raise NotImplementedError


class FractalTurbulent(EntrainRateBase):
    """分形湍流模型"""

    def __init__(self,
                 geometry: SITwoZoneGeometry,
                 flame_speed: Callable[[IdealGasReactor], Callable[[float], float]],
                 volume_fraction_to_stop: float = 0.001,
                 u_rms_0: float = 4,
                 reference_flame_radius: float = 0.006,
                 reference_engine_speed: float = 1000 / 60):
        """
        分形湍流燃烧模型
        :param geometry: 发动机几何
        :param flame_speed: 火焰速度计算类
        :param volume_fraction_to_stop: 结束时的未燃区体积百分比
        :param u_rms_0: 初始均方根湍流速度
        :param reference_flame_radius: 参考火焰半径 [m]
        :param reference_engine_speed: 参考转速 [r/s]
        """
        self._geometry = geometry  # 发动机几何
        self._flame_speed = flame_speed  # 火焰速度计算函数
        self._end_volume_fraction = volume_fraction_to_stop  # 结束时的未燃区体积百分比
        self._u_rms_0 = u_rms_0  # 初始均方根湍流速度
        self._reference_flame_radius = reference_flame_radius  # 参考火焰半径 [m]
        self._reference_engine_speed = reference_engine_speed  # 参考转速 [r/s]

        # 分形湍流燃烧模型计算中间参数
        self._tau: float = 0  # 特征时间尺度 [s]
        self._m_u_tr: float = 0  # 壁面燃烧切换时刻的未燃区质量 [kg]
        self._is_tr: float = False  # 是否开始分形与壁面燃烧切换

    def mass_flow_rate(self, burned: IdealGasReactor,
                       unburned: IdealGasReactor) -> Callable[[float], float]:
        """
        从未燃区到已燃区的质量流率 [kg/s]
        :param burned: 已燃区
        :param unburned: 未燃区
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
                if self._is_tr:
                    mass_u = unburned.mass  # 未燃区质量
                    w2 = 1 - mass_u / self._m_u_tr  # 近壁修正权重系数
                    return (1 - w2) * m_b_dot + w2 * (mass_u / self._tau)
                # 未达到近壁燃烧条件则返回原始燃烧速率
                else:
                    return m_b_dot

        return burning_rate
