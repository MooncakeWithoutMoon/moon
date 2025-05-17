# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2024/10/6
"""
__all__ = ['CylindricalCylinderGeometryComponent', 'OmigaCylinderGeometryComponent']

from dataclasses import dataclass

import esper
from numpy import pi

from ._component import Component
from ._crankshaft import CrankshaftComponent


@dataclass
class CylindricalCylinderGeometryComponent(Component):
    """圆柱形气缸组件, 即上下底面平整"""
    crankshaft_id: int = None  # 曲轴实体的id
    bore: float = 0.1  # 缸径 [m]
    compression_ratio: float = 10  # 压缩比

    @property
    def tdc_gap(self) -> float:
        """余隙高度 [m]"""
        if self.crankshaft_id is None:
            raise ValueError("Missing crankshaft !")
        crankshaft = esper.component_for_entity(self.crankshaft_id, CrankshaftComponent)
        return 2 * crankshaft.crank_radius / (self.compression_ratio - 1)

    @property
    def tdc_volume(self) -> float:
        """余隙容积 [m³]"""
        return self.tdc_gap * self.bore_area

    @property
    def bore_area(self) -> float:
        """气缸圆面积 [m²]"""
        return 0.25 * pi * self.bore ** 2


@dataclass
class OmigaCylinderGeometryComponent(Component):
    """具有 Omiga型线的气缸组件"""
    raise NotImplementedError
