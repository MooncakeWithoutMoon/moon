# -*- coding:utf-8 -*-
"""
提供各种燃烧反应机理
@Author: MoonCake Without Moon
@Time: 2025/2/17
"""
__all__ = ['Li', 'ARAOP', 'GRIMesh30', 'Issayev', 'UT_LCS']

import pathlib

_base_path = pathlib.Path(__file__).parent / 'yamls'  # yamls文件夹路径

# ARAOP机理, 甲醇-氢/重整气燃烧反应机理
ARAOP = _base_path / 'ARAOP.yaml'

# GRI-Mesh 3.0 机理, 甲烷燃烧反应机理
GRIMesh30 = 'gri30.yaml'

# Issayev机理, 氨-二甲醚反应机理
Issayev = _base_path / 'Issayev.yaml'

# Li 机理, 甲醇燃烧反应机理
Li = _base_path / 'Li.yaml'

# UT-LCS机理, 氨-氢氧化反应机理
UT_LCS = _base_path / 'UT-LCS.yaml'
