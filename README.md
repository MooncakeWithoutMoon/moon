# moon - 模块化发动机仿真框架
**论文发表后开源 The model will be open source after publication of the paper**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://python.org)
[![Cantera](https://img.shields.io/badge/dependency-Cantera-orange)](https://cantera.org)

moon是基于Cantera化学反应动力学库构建的准维发动机仿真平台实验性项目，采用创新的ECS（实体-组件-系统）架构设计，
为内燃机燃烧过程研究与稳态、动态性能仿真提供模块化解决方案。项目旨在建立可扩展的燃烧模型体系，
当前已实现点燃式发动机的分形湍流燃烧核心算法，并集成早期火焰发展修正与近壁燃烧效应修正。
## 核心特性
#### 🔥 先进燃烧建模
- 分形湍流燃烧模型（Fractal Turbulence Combustion Model）
- 早期火焰发展修正模型（Early Flame Development）
- 近壁面燃烧修正模型（Near-Wall Combustion）
#### 🛠 模块化架构
- 基于ECS架构实现数据与逻辑解耦
- 预置核心组件库：
  - 动力组件：曲轴、连杆、活塞组件、气缸、环境组件
  - 流动组件：进排气阀、燃油喷射器
  - 物理组件：燃烧模型、传热模型
#### ⚙️ 技术集成
- Cantera化学动力学求解核心
- 面向对象的Python API设计
- 基于FastAPI的http API设计（开发中）
- Godot图形用户界面（开发中）
## 快速开始


## 参与贡献
欢迎通过Issue提交改进建议或通过Pull Request参与开发
