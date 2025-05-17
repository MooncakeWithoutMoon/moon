# -*- coding:utf-8 -*-
"""
提供发动机几何计算工具
@Author: MoonCake Without Moon
@Time: 2025/1/23
"""
__all__ = ['EngineGeometry', 'SITwoZoneGeometry']

from functools import lru_cache

from numpy import pi, remainder, cos, sin, sqrt, linspace, concatenate
from scipy.interpolate import CloughTocher2DInterpolator

from ..tools.decorators import add_log


class EngineGeometry:
    """
    提供发动机几何计算工具, 例如曲轴转角、活塞速度等
    """

    def __init__(self,
                 speed: float,
                 stroke: float,
                 epsilon: float,
                 bore: float,
                 crank_rod_ratio: float,
                 tdc_gap: float):
        self.speed = speed  # 转速 [r/s]
        self.stroke = stroke  # 冲程 [m]
        self.epsilon = epsilon  # 压缩比
        self.bore = bore  # 缸径 [m]
        self.crank_rod_ratio = crank_rod_ratio  # 曲柄连杆比
        self.tdc_gap = tdc_gap  # 余隙高度 [m]


    @lru_cache
    def crank_angle(self, time: float) -> float:
        """
        曲轴转角
        :param time: 时间 [s]
        :return: 曲轴转角 [rad]
        """
        return remainder(2 * pi * self.speed * time, 4 * pi)

    @lru_cache
    def piston_position(self, time: float) -> float:
        """
        活塞位置
        :param time: 时间 [s]
        :return: 活塞位置 (以缸盖为0点, 向下为正) [m]
        """
        angle = self.crank_angle(time)
        return (self.stroke / 2 * ((1 + 1 / self.crank_rod_ratio) - cos(angle) - 1 / self.crank_rod_ratio *
                                   sqrt(1 - self.crank_rod_ratio ** 2 * sin(angle) ** 2)) + self.tdc_gap)

    @lru_cache
    def piston_velocity(self, time: float) -> float:
        """
        活塞速度
        :param time: 时间 [s]
        :return: 活塞速度 (向下为正) [m/s]
        """
        angle = self.crank_angle(time)
        return self.stroke * (self.crank_rod_ratio * sin(angle) * cos(angle) /
                              sqrt(-self.crank_rod_ratio ** 2 * sin(angle) ** 2 + 1)
                              + sin(angle)) * pi * self.speed

    @lru_cache
    def cylinder_volume(self, time: float) -> float:
        """
        气缸容积
        :param time: 时间 [s]
        :return: 气缸容积 [m**3]
        """
        angle = self.crank_angle(time)
        return (pi * self.bore ** 2 / 4 *
                (self.stroke / (self.epsilon - 1) + self.stroke / 2 *
                 ((1 + 1 / self.crank_rod_ratio) - cos(angle) - 1 / self.crank_rod_ratio *
                  sqrt(1 - self.crank_rod_ratio ** 2 * sin(angle) ** 2))))

    @property
    def mean_piston_speed(self) -> float:
        """
        活塞平均速度
        :return: 活塞平均速度 [m/s]
        """
        return self.speed * self.stroke * 2

    @property
    def tdc_volume(self) -> float:
        """
        余隙容积
        :return: 余隙容积 [m**3]
        """
        return pi * self.bore ** 2 / 4 * self.stroke / (self.epsilon - 1)

    @property
    def working_volume(self) -> float:
        """
        工作容积, 即气缸排量
        :return: 工作容积 [m**3]
        """
        return pi * self.bore ** 2 / 4 * self.stroke

    @property
    def area_bore(self) -> float:
        """
        气缸圆的面积
        :return: 气缸圆的面积 [m**2]
        """
        return pi * self.bore ** 2 / 4


class SITwoZoneGeometry(EngineGeometry):
    """
    提供点燃式发动机双区域发动机几何计算工具, 适用于理想圆柱气缸 (活塞顶为平面), 除了基本的发动机几何外,
    还包括双区几何计算工具, 例如火焰面积、周壁传热面积等
    """

    def __init__(self,
                 speed: float,
                 stroke: float,
                 epsilon: float,
                 bore: float,
                 crank_rod_ratio: float):
        tdc_gap = stroke / (epsilon - 1)  # 余隙高度 [m]
        super().__init__(
            speed, stroke, epsilon, bore, crank_rod_ratio, tdc_gap
        )
        self._flame_radius_interpolator: CloughTocher2DInterpolator | None = None  # 火焰半径插值

    @lru_cache
    def flame_radius(self, time: float, burned_volume_percentage: float) -> float:
        """
        火焰半径
        :param time: 时间 [s]
        :param burned_volume_percentage: 已燃体积百分比 (已燃体积 / 当前气缸总体积)
        :return: 火焰半径 [m]
        """
        h_gap = self.piston_position(time)
        if self._flame_radius_interpolator is None:
            self._flame_radius_interpolator = self._interp()
        return self._flame_radius_interpolator(h_gap, burned_volume_percentage)

    @lru_cache
    def flame_area(self, time: float, burned_volume_percentage: float) -> float:
        """
        火焰面积
        :param time: 时间 [s]
        :param burned_volume_percentage: 已燃体积百分比 (已燃体积 / 当前气缸总体积)
        :return: 火焰面积 [m**2]
        """
        h_gap = self.piston_position(time)
        r_f = self.flame_radius(time, burned_volume_percentage)
        return self._a_f(r_f, self._alpha(r_f), self._beta(h_gap, r_f))

    @lru_cache
    def burned_cover_area(self, time: float, burned_volume_percentage: float) -> float:
        """
        已燃区与缸盖接触的面积
        :param time: 时间 [s]
        :param burned_volume_percentage: 已燃体积百分比 (已燃体积 / 当前气缸总体积)
        :return: 已燃区与缸盖接触的面积 [m**2]
        """
        r_f = self.flame_radius(time, burned_volume_percentage)
        if r_f < self.bore / 2:
            return pi * r_f ** 2
        else:
            return self.area_bore

    @lru_cache
    def burned_wall_area(self, time: float, burned_volume_percentage: float) -> float:
        """
        已燃区与气缸壁接触的面积
        :param time: 时间 [s]
        :param burned_volume_percentage: 已燃体积百分比 (已燃体积 / 当前气缸总体积)
        :return: 已燃区与气缸壁接触的面积 [m**2]
        """
        r_f = self.flame_radius(time, burned_volume_percentage)
        if r_f < self.bore / 2:
            return 0
        else:
            return sqrt(r_f ** 2 - (self.bore / 2) ** 2) * pi * self.bore

    @lru_cache
    def burned_piston_area(self, time: float, burned_volume_percentage: float) -> float:
        """
        已燃区与活塞顶端接触的面积
        :param time: 时间 [s]
        :param burned_volume_percentage: 已燃体积百分比 (已燃体积 / 当前气缸总体积)
        :return: 已燃区与活塞顶端接触的面积 [m**2]
        """
        r_f = self.flame_radius(time, burned_volume_percentage)
        h_gap = self.piston_position(time)
        if r_f < h_gap:
            return 0
        else:
            return (r_f ** 2 - h_gap ** 2) * pi

    def unburned_cover_area(self, time: float, burned_volume_percentage: float) -> float:
        """
        未燃区与缸盖接触的面积
        :param time: 时间 [s]
        :param burned_volume_percentage: 已燃体积百分比 (已燃体积 / 当前气缸总体积)
        :return: 未燃区与缸盖接触的面积 [m**2]
        """
        return self.area_bore - self.burned_cover_area(time, burned_volume_percentage)

    def unburned_wall_area(self, time: float, burned_volume_percentage: float) -> float:
        """
        未燃区与气缸壁接触的面积
        :param time: 时间 [s]
        :param burned_volume_percentage: 已燃体积百分比 (已燃体积 / 当前气缸总体积)
        :return: 未燃区与气缸壁接触的面积 [m**2]
        """
        return (self.piston_position(time) * pi * self.bore -
                self.burned_wall_area(time, burned_volume_percentage))

    def unburned_piston_area(self, time: float, burned_volume_percentage: float) -> float:
        """
        未燃区与活塞顶端接触的面积
        :param time: 时间 [s]
        :param burned_volume_percentage: 已燃体积百分比 (已燃体积 / 当前气缸总体积)
        :return: 未燃区与活塞顶端接触的面积 [m**2]
        """
        return self.area_bore - self.burned_piston_area(time, burned_volume_percentage)

    def _alpha(self, r_f: float) -> float:
        """
        火焰半径计算系数 alpha
        :param r_f: 火焰半径 [m]
        :return: alpha
        """
        if 2 * r_f / self.bore < 1:
            return 0
        else:
            return sqrt(1 - (0.5 * self.bore / r_f) ** 2)

    @staticmethod
    def _beta(h_gap: float, r_f: float) -> float:
        """
        火焰半径计算系数 beta
        :param h_gap: 活塞顶到缸盖的距离 [m]
        :param r_f: 火焰半径 [m]
        :return: beta
        """
        if r_f < h_gap:
            return 1
        else:
            return h_gap / r_f

    def _v_f(self, r_f: float, alpha: float, beta: float) -> float:
        """
        已燃区体积
        :param r_f: 火焰半径 [m]
        :param alpha: 计算系数 alpha
        :param beta: 计算系数 beta
        :return: 已燃区体积 [m**3]
        """
        return (0.125 * pi * self.bore ** 3 *
                ((1 / 3 * (2 * r_f / self.bore) ** 3 *
                  (alpha ** 3 - beta ** 3 - 3 * (alpha - beta))) + 2 * r_f / self.bore * alpha))

    def _a_f(self, r_f: float, alpha: float, beta: float) -> float:
        """
        火焰面积
        :param r_f: 火焰半径 [m]
        :param alpha: 计算系数 alpha
        :param beta: 计算系数 beta
        :return: 火焰面积 [m**2]
        """
        return self.area_bore * (2 * (2 * r_f / self.bore) ** 2 * (beta - alpha))

    # @add_log('正在计算火焰面几何数据', '火焰面几何数据计算完成')
    def _interp(self) -> CloughTocher2DInterpolator:
        """
        计算火焰半径插值
        :return: 火焰半径插值 (h_gap, v_f_v)
        """
        v_f_v_interp = []  # 用于插值的已燃体积百分比
        h_gap_interp = []  # 用于插值的气缸高度
        r_f_interp = []  # 用于插值的火焰半径
        h_gaps = linspace(self.tdc_gap, self.tdc_gap + self.stroke, 50)
        for h_gap in h_gaps:
            r_max = sqrt((self.bore / 2) ** 2 + h_gap ** 2)
            # 缩小半径较小时的步长, 保证在火焰面积较小时有足够的解析度
            r_f_s1 = linspace(0, self.bore / 10, 20)
            r_f_s2 = linspace(self.bore / 10, r_max, 80)
            r_f_s = concatenate((r_f_s1, r_f_s2))
            for r_f in r_f_s:
                alpha = self._alpha(r_f)
                beta = self._beta(h_gap, r_f)
                v_f_v_interp.append(self._v_f(r_f, alpha, beta) / (self.area_bore * h_gap))
                h_gap_interp.append(h_gap)
                r_f_interp.append(r_f)
        return CloughTocher2DInterpolator(list(zip(h_gap_interp, v_f_v_interp)), r_f_interp)
