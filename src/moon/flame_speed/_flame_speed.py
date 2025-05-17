# -*- coding:utf-8 -*-
"""
提供多种未拉伸的层流火焰速度计算方法, 使用策略模式
@Author: MoonCake Without Moon
@Time: 2024/10/10
"""
__all__ = ['FlameSpeedBase', 'FlameSpeedContext', 'MethanolHydrogenFlameSpeed']

import pathlib
from abc import ABC, abstractmethod

from numpy import array, sum
from pandas import read_csv
from cantera import IdealGasReactor
from loguru import logger


class FlameSpeedBase(ABC):
    """
    策略接口
    """

    def __init__(self, unburned: IdealGasReactor):
        """
        策略接口
        :param unburned: 未燃区反应器
        """
        self.unburned = unburned  # 未燃区反应器

    @abstractmethod
    def laminar_flame_speed(self) -> float:
        """
        层流火焰速度接口
        :return: 层流火焰速度 [m/s]
        """
        pass


class FlameSpeedContext:
    """
    火焰速度策略上下文
    """

    def __init__(self, flame_speed: FlameSpeedBase):
        """
        火焰速度策略上下文
        :param flame_speed: 层流火焰速度策略类
        """
        # 判断是否继承FlameSpeedBase接口
        if not isinstance(flame_speed, FlameSpeedBase):
            raise TypeError('flame_speed must inherit FlameSpeedBase')
        self.strategy = flame_speed  # 层流火焰速度计算策略类

    def laminar_flame_speed(self) -> float:
        """
        执行策略计算层流火焰速度
        :return: 层流火焰速度 [m/s]
        """
        return self.strategy.laminar_flame_speed()


class MethanolHydrogenFlameSpeed(FlameSpeedBase):
    """
    甲醇-氢火焰速度
    """

    def __init__(self, unburned: IdealGasReactor, boundary_warning: bool = True):
        """
        甲醇-氢火焰速度
        :param unburned: 未燃区反应器
        :param boundary_warning: 是否发出参数越界警告
        """
        super().__init__(unburned)
        self.boundary_warning = boundary_warning  # 是否发出参数越界警告
        self._data_ranges = {
            'equivalence ratio': {'range': (0.6, 1.5), 'unit': None},
            'unburned gas temperature': {'range': (400, 2600), 'unit': 'K'},
            'pressure': {'range': (1e5, 5e6), 'unit': 'Pa'},
            'residual gas mass fraction': {'range': (0, 0.2), 'unit': None},
            'hydrogen volume fraction': {'range': (0, 0.1), 'unit': None}
        }  # 数据范围
        current_path = pathlib.Path(__file__).parent  # 当前文件所在文件夹路径
        relative_path = r'fit_coefficients/hydrogen_methanol.csv'  # 相对路径
        absolute_path = current_path / relative_path  # 绝对路径
        # 拟合系数
        fit_coefficients = read_csv(absolute_path, index_col=0)
        self._a_lower = array(fit_coefficients['a_lower'].dropna())
        self._a_upper = array(fit_coefficients['a_upper'].dropna())
        self._b_lower = array(fit_coefficients['b_lower'].dropna())
        self._b_upper = array(fit_coefficients['b_upper'].dropna())
        self._c = array(fit_coefficients['c'].dropna())
        self._d = array(fit_coefficients['d'].dropna())
        self._T_ref = 400  # 参考温度 [K]
        self._p_ref = 1e5  # 参考压力 [Pa]
        self._CO2_index = self.unburned.thermo.species_index('CO2')  # CO2索引
        self._H2_index = self.unburned.thermo.species_index('H2')  # H2索引

    def laminar_flame_speed(self) -> float:
        """
        层流火焰速度
        :return: 层流火焰速度 [m/s]
        """
        phi = self.unburned.thermo.equivalence_ratio()
        t_u = self.unburned.thermo.T
        p = self.unburned.thermo.P
        # CO2质量分数到残余气体质量分数的映射, 基于纯甲醇燃烧推导得到
        y_dil = self.unburned.thermo.Y[self._CO2_index] * 32 * (phi + 6.43715625) / (44 * phi)
        alpha_h2 = self.unburned.thermo.X[self._H2_index]
        # 对各参数做范围检查
        if self.boundary_warning is True:
            values = [phi, t_u, p, y_dil, alpha_h2]
            for key, value in zip(self._data_ranges.keys(), values):
                self._check_parameter(key, value)
        s_l = self._s_l(phi, t_u, p, y_dil, alpha_h2)
        # 确保层流火焰速度大于0
        return max(s_l, 0)

    def _s_l(self, phi: float, t_u: float, p: float, y_dil: float, alpha_h2: float) -> float:
        """
        计算层流火焰速度
        :param phi: 当量比
        :param t_u: 未燃气体温度 [K]
        :param p: 压力 [Pa]
        :param y_dil: 残余气体质量分数
        :param alpha_h2: 氢气体积分数
        :return: 层流火焰速度 [m/s]
        """
        # matrix_1为计算SL_0、alpha、和gama的系数矩阵
        matrix_1 = array(
            [1, phi, phi ** 2, alpha_h2, alpha_h2 ** 2, phi * alpha_h2,
             phi ** 2 * alpha_h2, phi * alpha_h2 ** 2, phi ** 2 * alpha_h2 ** 2]
        )
        # matrix_2为计算Beta的系数矩阵
        t_t_ref = t_u / self._T_ref
        matrix_2 = array(
            [1, phi, phi ** 2, alpha_h2, alpha_h2 ** 2, t_t_ref, t_t_ref ** 2,
             phi * alpha_h2, phi * t_t_ref, alpha_h2 * t_t_ref,
             phi ** 2 * alpha_h2, phi * alpha_h2 ** 2, phi ** 2 * alpha_h2 ** 2,
             phi * t_t_ref ** 2, alpha_h2 * t_t_ref ** 2]
        )
        if phi <= 1:
            s_l0 = sum(self._a_lower * matrix_1)
            alpha = sum(self._b_lower * matrix_1)
        else:
            s_l0 = sum(self._a_upper * matrix_1)
            alpha = sum(self._b_upper * matrix_1)
        beta = sum(self._c * matrix_2)
        gamma = sum(self._d * matrix_1)
        return s_l0 * t_t_ref ** alpha * (p / self._p_ref) ** beta * (1 - gamma * y_dil) * 1e-2

    def _check_parameter(self, key: str, value: float) -> None:
        """
        对当量比等参数进行范围检查, 如果超出范围则会抛出警告
        :param key: 需检查的参数
        :param value: 需检查的值
        """
        if not (self._data_ranges[key]['range'][0] <= value <= self._data_ranges[key]['range'][1]):
            logger.warning(f"{key} is out of range, the range is {self._data_ranges[key]['range'][0]}"
                           f" to {self._data_ranges[key]['range'][1]}, you can set the boundary_warning"
                           f" to False to ignore this warning.")

    @property
    def data_ranges(self) -> dict:
        """
        数据范围
        """
        return self._data_ranges
