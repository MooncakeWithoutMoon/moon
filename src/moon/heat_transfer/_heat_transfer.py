# -*- coding:utf-8 -*-
"""
提供各种气缸周壁传热计算方法, 策略模式
@Author: MoonCake Without Moon
@Time: 2025/1/22
"""
__all__ = [
    'HeatTransferBase', 'HeatTransferContext', 'MotoredCylinder',
    'Woschni', 'Hohenberg', 'Eichelberg', 'Sitkel'
]

from abc import ABC, abstractmethod
from typing import Callable

from cantera import IdealGasReactor, Solution, Reservoir, Valve, ReactorNet, Wall
from numpy import cbrt, sqrt, pi, linspace
from scipy.interpolate import interp1d

from ..geometry import EngineGeometry


class HeatTransferBase(ABC):
    """
    传热接基类
    """

    def __init__(self,
                 cover_temperature: float = 400,
                 wall_temperature: float = 400,
                 crown_temperature: float = 500):
        """
        传热基类
        :param cover_temperature: 缸盖温度 [K]
        :param wall_temperature: 缸壁温度 [K]
        :param crown_temperature: 活塞冠温度 [K]
        """
        self.cover_temperature = cover_temperature
        self.wall_temperature = wall_temperature
        self.crown_temperature = crown_temperature

    @abstractmethod
    def _alpha(self, time: float) -> float:
        """
        传热系数
        :param time: 仿真时间 [s]
        :return: 传热系数 [W/(m**2*K)]
        """
        pass

    @abstractmethod
    def heat_transfer_coefficient(self, reactor: IdealGasReactor,
                                  geometry: EngineGeometry) -> Callable[[float], float]:
        """
        传热系数
        :param reactor: 反应器
        :param geometry: 几何类
        :return: 传热系数计算函数
        """
        pass


class HeatTransferContext:
    """
    传热策略上下文
    """

    def __init__(self, heat_transfer: HeatTransferBase):
        """
        传热策略上下文
        :param heat_transfer: 传热策略类
        """
        # 判断是否继承HeatTransferBase接口
        if not isinstance(heat_transfer, HeatTransferBase):
            raise TypeError('heat_transfer must inherit HeatTransferBase')
        self.heat_transfer = heat_transfer

    def heat_transfer_coefficient(self, reactor: IdealGasReactor,
                                  geometry: EngineGeometry) -> Callable[[float], float]:
        """
        传热系数
        :param reactor: 反应器
        :param geometry: 几何类
        :return: 传热系数计算函数
        """
        return self.heat_transfer.heat_transfer_coefficient(reactor, geometry)


class Hohenberg(HeatTransferBase):
    """
    Hohenberg传热

        由 Hohenberg提出, 他认为 Woschni传热存在一定的精度缺陷, 即压缩过程中的传热系数估计过低,
        燃烧过程中的传热系数估计过高, 导致整个循环的平均热流密度偏高。
        因此提出了 Hohenberg传热公式, 公式形式相较于 Woschni传热更为简单。
    """

    def __init__(self,
                 cover_temperature: float = 400,
                 wall_temperature: float = 400,
                 crown_temperature: float = 500):
        """
        Hohenberg传热
        :param cover_temperature: 缸盖温度 [K]
        :param wall_temperature: 缸壁温度 [K]
        :param crown_temperature: 活塞冠温度 [K]
        """
        super().__init__(cover_temperature, wall_temperature, crown_temperature)
        self._reactor: IdealGasReactor | None = None  # 反应器
        self._geometry: EngineGeometry | None = None  # 发动机几何
        self._c_m: float | None = None  # 活塞平均速度 [m/s]

    def _alpha(self, time: float) -> float:
        """
        传热系数
        :param time: 仿真时间 [s]
        :return: 传热系数 [W/(m**2*K)]
        """
        v_c = self._geometry.cylinder_volume(time)  # 气缸容积 [m³]
        return (1.3e-2 * v_c ** -0.06 * self._reactor.thermo.P ** 0.8 *
                self._reactor.T ** -0.4 * (1.4 + self._c_m) ** 0.8)

    def heat_transfer_coefficient(self, reactor: IdealGasReactor,
                                  geometry: EngineGeometry) -> Callable[[float], float]:
        self._reactor = reactor
        self._geometry = geometry
        self._c_m = geometry.mean_piston_speed
        return self._alpha


class Eichelberg(HeatTransferBase):
    """
    Eichelberg传热

        适用于非增压、低速大型二冲程柴油机, 形式简单, 计算速度较快
    """

    def __init__(self,
                 cover_temperature: float = 400,
                 wall_temperature: float = 400,
                 crown_temperature: float = 500):
        """
        Eichelberg传热, 适用于非增压、低速大型二冲程柴油机, 形式简单, 计算速度较快
        :param cover_temperature: 缸盖温度 [K]
        :param wall_temperature: 缸壁温度 [K]
        :param crown_temperature: 活塞冠温度 [K]
        """
        super().__init__(cover_temperature, wall_temperature, crown_temperature)
        self._reactor: IdealGasReactor | None = None  # 反应器
        self._geometry: EngineGeometry | None = None  # 发动机几何
        self._c_m: float | None = None  # 活塞平均速度 [m/s]

    def _alpha(self, time: float) -> float:
        """
        传热系数
        :param time: 仿真时间 [s]
        :return: 传热系数 [W/(m**2*K)]
        """
        return 7.79e-3 * cbrt(self._c_m) * sqrt(self._reactor.thermo.P * self._reactor.T)

    def heat_transfer_coefficient(self, reactor: IdealGasReactor,
                                  geometry: EngineGeometry) -> Callable[[float], float]:
        self._reactor = reactor
        self._geometry = geometry
        self._c_m = geometry.mean_piston_speed
        return self._alpha


class Sitkel(HeatTransferBase):
    """
    Sitkel传热

        适用于小型柴油机
    """

    def __init__(self,
                 combustion_chamber_type: str = 'direct injection',
                 cover_temperature: float = 400,
                 wall_temperature: float = 400,
                 crown_temperature: float = 500):
        """
        Sitkel传热, 适用于小型柴油机
        :param combustion_chamber_type: 燃烧室类型
                                        (直喷式燃烧室 'direct injection'
                                         涡流室式燃烧室 'vortex chamber'
                                         预燃室式燃烧室 'pre-chamber')
        :param cover_temperature: 缸盖温度 [K]
        :param wall_temperature: 缸壁温度 [K]
        :param crown_temperature: 活塞冠温度 [K]
        """
        super().__init__(cover_temperature, wall_temperature, crown_temperature)
        self._reactor: IdealGasReactor | None = None  # 反应器
        self._geometry: EngineGeometry | None = None  # 发动机几何
        self._c_m: float | None = None  # 活塞平均速度 [m/s]
        self._bore: float | None = None  # 缸径 [m]
        # 经验常数
        match combustion_chamber_type:
            case 'direct injection':
                self._b = 0.08
            case 'vortex chamber':
                self._b = 0.2
            case 'pre-chamber':
                self._b = 0.3
            case _:
                raise TypeError("combustion_chamber_type must be 'direct injection', 'vortex chamber'"
                                "or 'pre-chamber'")

    def _alpha(self, time: float) -> float:
        """
        传热系数
        :param time: 时间 [s]
        :return: 传热系数 [W/(m**2*K)]
        """
        h_gap = self._geometry.piston_position(time)  # 活塞与缸盖距离
        d_e = (2 * self._bore * h_gap) / (self._bore + 2 * h_gap)  # 当量直径
        return (1.294e-5 * (1 + self._b) * d_e ** -0.3 * self._reactor.T ** -0.2 *
                (self._reactor.thermo.P * self._c_m) ** 0.7)

    def heat_transfer_coefficient(self, reactor: IdealGasReactor, geometry: EngineGeometry) -> Callable[[float], float]:
        self._reactor = reactor
        self._geometry = geometry
        self._c_m = geometry.mean_piston_speed
        self._bore = geometry.bore
        return self._alpha


# TODO: 完善 Woschni 模型

class MotoredCylinder:
    """
    倒拖缸
    """

    def __init__(self,
                 mechanism: str,
                 geometry: EngineGeometry,
                 tpx_inlet: tuple,
                 tpx_outlet: tuple,
                 inlet_valve_coeffs: list,
                 inlet_valve_time_funcs: list,
                 outlet_valve_coeffs: list,
                 outlet_valve_time_funcs: list,
                 cover_temperature: float = 400,
                 wall_temperature: float = 400,
                 crown_temperature: float = 500,
                 interp_num: int = 360,
                 interp_kind: str = 'cubic'
                 ):
        self.mechanism = mechanism  # 反应机理
        self.geometry = geometry  # 发动机几何
        self.tpx_inlet = tpx_inlet  # 进气环境
        self.tpx_outlet = tpx_outlet  # 排气环境
        self.inlet_valve_coeffs = inlet_valve_coeffs  # 进气阀系数
        self.inlet_valve_time_funcs = inlet_valve_time_funcs  # 进气阀时间函数
        self.outlet_valve_coeffs = outlet_valve_coeffs  # 排气阀系数
        self.outlet_valve_time_funcs = outlet_valve_time_funcs  # 排气阀时间函数
        self.cover_temperature = cover_temperature  # 缸盖温度 [K]
        self.wall_temperature = wall_temperature  # 缸壁温度 [K]
        self.crown_temperature = crown_temperature  # 活塞冠温度 [K]
        self.interp_num: int = interp_num  # 倒拖缸压插值点数
        self.interp_kind: str = interp_kind  # 倒拖缸压插值类型
        self.c1 = 3.26
        self._wt_cm = 10
        self.c3_gas_exchange = 6.18 + 0.417 * self._wt_cm
        self.c3_in_cylinder = 2.28 + 0.308 * self._wt_cm
        self._d = self.geometry.bore  # 缸径 [m]
        self._cm = self.geometry.mean_piston_speed  # 活塞平均速度 [m/s]
        self._area = self.geometry.area_bore  # 气缸圆的面积 [m**2]
        self._motored_pressure: interp1d | None = None  # 倒拖缸压

    # @add_log('正在构建倒拖缸', '倒拖缸构建完成')
    def _build_motored_cylinder(self) -> IdealGasReactor:
        """
        构建倒拖缸
        :return: 倒拖缸反应器
        """
        gas = Solution(self.mechanism)
        # 排气环境
        gas.TPX = self.tpx_outlet
        ambient_outlet = Reservoir(gas)
        # 进气环境
        gas.TPX = self.tpx_inlet
        ambient_inlet = Reservoir(gas)
        # 气缸
        cylinder = IdealGasReactor(gas)
        cylinder.chemistry_enabled = False  # 关闭化学反应
        cylinder.volume = self.geometry.tdc_volume
        inlet_valves = []
        outlet_valves = []
        # 进气阀
        for c, tf in zip(self.inlet_valve_coeffs, self.inlet_valve_time_funcs):
            inlet_valve = Valve(ambient_inlet, cylinder)
            inlet_valve.valve_coeff = c
            inlet_valve.time_function = tf
            inlet_valves.append(inlet_valve)
        # 排气阀
        for c, tf in zip(self.outlet_valve_coeffs, self.outlet_valve_time_funcs):
            outlet_valve = Valve(cylinder, ambient_outlet)
            outlet_valve.valve_coeff = c
            outlet_valve.time_function = tf
            outlet_valves.append(outlet_valve)
        piston = Wall(cylinder, ambient_outlet)
        piston.area = self.geometry.area_bore
        piston.velocity = self.geometry.piston_velocity

        def motored_heat_transfer_coefficient(time: float) -> float:
            """
            倒拖缸传热系数
            :param time: 时间 [s]
            :return: 传热系数 [W/(m**2*K)]
            """
            angle = self.geometry.crank_angle(time)
            if angle >= self.geometry.eo_angle or angle < self.geometry.ic_angle:
                c3 = self.c3_gas_exchange
            else:
                c3 = self.c3_in_cylinder
            p = cylinder.thermo.P  # 缸内压力 [Pa]
            t = cylinder.T  # 缸内温度 [K]
            return self.c1 * self._d ** -0.214 * (0.001 * p) ** 0.786 * t ** -0.525 * c3 * self._cm

        def motored_heat_flux(time: float) -> float:
            """
            倒拖缸热通量 (换算为气缸周壁传热全部从活塞传热的热通量)
            :param time: 时间 [s]
            :return: 热通量 [W/(m**2)]
            """
            a_cover = self._area
            a_wall = self.geometry.piston_position(time) * pi * self.geometry.bore
            a_crown = self._area * 1.3
            t = cylinder.T
            return (((t - self.cover_temperature) * a_cover +
                     (t - self.wall_temperature) * a_wall +
                     (t - self.crown_temperature) * a_crown) *
                    motored_heat_transfer_coefficient(time) / self._area)

        piston.heat_flux = motored_heat_flux  # 设置传热通量
        return cylinder

    # @add_log('正在求解倒拖缸压', '倒拖缸压求解完成')
    def _calculate_motored_pressure(self) -> interp1d:
        """
        求解倒拖缸压
        :return: 倒拖缸压插值
        """
        cylinder = self._build_motored_cylinder()
        reactor_net = ReactorNet([cylinder])
        angles = linspace(0, 4 * pi, self.interp_num)
        times = angles / (2 * pi * self.geometry.speed)
        pressures = []
        # 步进cantera求解器
        for time in times:
            reactor_net.advance(time)
            pressures.append(cylinder.thermo.P)
        return interp1d(angles, pressures, kind=self.interp_kind)

    @property
    def motored_pressure(self) -> interp1d:
        """
        倒拖缸压
        :return: 倒拖缸压的曲轴转角插值 [rad] [Pa]
        """
        if self._motored_pressure is None:
            self._motored_pressure = self._calculate_motored_pressure()
            return self._motored_pressure
        else:
            return self._motored_pressure

    def update_motored_pressure(self) -> None:
        """
        更新倒拖缸压插值
        """
        self._motored_pressure = self._calculate_motored_pressure()


class Woschni(HeatTransferBase):
    """
    Woschni传热
    """

    def __init__(self,
                 reactor: IdealGasReactor,
                 geometry: EngineGeometry,
                 motored_pressure: interp1d,
                 inlet_pressure: float,
                 inlet_temperature: float,
                 combustion_chamber_type: str = 'direct injection'):
        """
        Woschni传热
        :param reactor: 反应器
        :param geometry: 发动机几何
        :param motored_pressure: 倒拖缸压插值 (关于曲轴转角 [rad] 的插值)
        :param inlet_pressure: 进气压力 [Pa]
        :param inlet_temperature: 进气温度 [K]
        :param combustion_chamber_type: 燃烧室类型 直喷 'direct injection' 或 预燃室 'pre_chamber'
        """
        self.reactor = reactor  # 反应器
        self.geometry = geometry  # 发动机几何
        self.motored_pressure = motored_pressure  # 倒拖缸压
        self.inlet_pressure = inlet_pressure  # 进气压力 [Pa]
        self.inlet_temperature = inlet_temperature  # 进气温度 [K]
        self.combustion_chamber_type = combustion_chamber_type  # 燃烧室类型
        self.c1 = 1.3e-2
        self._wt_cm = 10
        self.c3_gas_exchange = 6.18 + 0.417 * self._wt_cm
        self.c3_in_cylinder = 2.28 + 0.308 * self._wt_cm
        match self.combustion_chamber_type:
            case 'direct injection':
                self.c4 = 0.00324
            case 'pre_chamber':
                self.c4 = 0.00622
            case _:
                raise ValueError("combustion_chamber_type must be 'direct injection' or 'pre_chamber'")
        self._v1 = self.geometry.ic_volume  # 进气阀关闭时的体积 [m**3]
        self._vs = self.geometry.working_volume  # 工作容积 [m**3]
        self._bore = self.geometry.bore  # 缸径 [m]
        self._cm = self.geometry.mean_piston_speed  # 活塞平均速度 [m/s]

    def _alpha(self, time: float) -> float:
        """
        传热系数
        :param time: 时间 [s]
        :return: 传热系数 [W/(m**2*K)]
        """
        angle = self.geometry.crank_angle(time)
        if angle >= self.geometry.eo_angle or angle < self.geometry.ic_angle:
            c3 = self.c3_gas_exchange
        else:
            c3 = self.c3_in_cylinder
        p0 = self.motored_pressure(angle)  # 倒拖缸压 [Pa]
        p = self.reactor.thermo.P  # 缸内压力 [Pa]
        t = self.reactor.T  # 缸内温度 [K]
        return (self.c1 * self._bore ** -0.214 * p ** 0.786 * t ** -0.525 *
                (c3 * self._cm + self.c4 * (p - p0) / self.inlet_pressure *
                 self._vs / self._v1 * self.inlet_temperature) ** 0.786)
