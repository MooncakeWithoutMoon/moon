# -*- coding:utf-8 -*-
"""
@Author: MoonCake Without Moon
@Time: 2025/4/26
"""
from cantera import IdealGasReactor
from cantera import Valve as ct_Valve


class ReactorNetworkResource:
    """反应器网络资源"""

    def __init__(self):
        self.reactors: list[IdealGasReactor] = []  # 反应器
        self.valves: list[ct_Valve] = []  # 阀门
