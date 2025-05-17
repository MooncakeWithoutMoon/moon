# 壁面传热

包含了关于壁面传热相关的介绍。

## 热流量

### 单区模型

TODO: 介绍单区模型热流量计算

### SI发动机双区模型

TODO: 介绍双区模型热流量计算

## 传热系数

### Woschni传热

`Woschni`传热是最常用的缸内传热计算方法, 由Woschni开发。

$$
\alpha_{gas \to wall} = C_1 \cdot B^{-0.214} \cdot P^{0.786} \cdot T^{-0.525} \cdot
\left[C_3 \cdot c_m + C_4 \cdot \frac{P-P_0}{P_1} \cdot \frac{V_s}{V_1} \cdot T_1 \right] ^ {0.786}
$$

- $\alpha_{gas \to wall}$: 传热系数 (W/(m²·K))
- $B$: 气缸直径 (m)
- $P$: 缸内压力 (Pa)
- $T$: 缸内温度 (K)
- $c_m$: 活塞平均速度 (m/s)
- $P_1$: 参考压力, 即进气阀关闭时的压力 (Pa)
- $V_1$: 参考容积, 即进气阀关闭时的气缸容积 (m³)
- $T_1$: 参考温度, 即进气阀关闭时的缸内温度 (K)
- $P_0$: 倒拖缸压, 即没有发生燃烧的缸内压力 (Pa)
- $C_1$: 常数, $C_1=1.3 \times 10^{-2}$
- $C_3$: 常数, 计算方法见下方
- $C_4$: 常数, 计算方法见下方

$C_3$与缸内涡旋速度 $w_t$ 有关, Woschni建议采用以下的方法计算:

换气阶段:

$$
C_3 = 6.18 + 0.417 \cdot \frac{w_t}{c_m}
$$

压缩, 燃烧, 膨胀阶段:

$$
C_3 = 2.28 + 0.308 \cdot \frac{w_t}{c_m}
$$

$w_t/c_m$通常取5~50范围。

$C_4$与燃烧室类型有关:

换气和压缩阶段:

$$
C_4 = 0
$$

燃烧和膨胀阶段:

$$
直喷式燃烧室:C_4 = 0.00324
$$

$$
预燃室式燃烧室:C_4 = 0.00622
$$

### Hohenberg传热

`Hohenberg`传热由Hohenberg提出, 他认为Woschni传热存在一定的精度缺陷, 即压缩过程中的传热系数估计过低,
燃烧过程中的传热系数估计过高, 导致整个循环的平均热流密度偏高。因此提出了Hohenberg传热公式, 公式形式相较于
Woschni传热更为简单。

$$
\alpha_{gas \to wall} = C_1 \cdot V_c^{-0.06} \cdot P^{0.8} \cdot T^{-0.4} \cdot
\left( C_2 + c_m \right)^{0.8}
$$

- $\alpha_{gas \to wall}$: 传热系数 (W/(m²·K))
- $V_c$: 气缸容积 (m³)
- $P$: 缸内压力 (Pa)
- $T$: 缸内温度 (K)
- $c_m$: 活塞平均速度 (m/s)
- $C_1$: 常数, $C_1 = 1.3 \times 10^{-2}$
- $C_2$: 常数, $C_2 = 1.4$

### Eichelberg传热

`Eichelberg`传热是纯经验公式, 适用于**非增压**, **低速大型二冲程**柴油机, 计算公式简单, 不存在任何待定系数。

$$
\alpha_{gas \to wall} = 7.79 \times 10^{-3} \sqrt[3]{c_m} \cdot \sqrt{PT}
$$

- $\alpha_{gas \to wall}$: 传热系数 (W/(m²·K))
- $c_m$: 活塞平均速度 (m/s)
- $P$: 缸内压力 (Pa)
- $T$: 缸内温度 (K)

### Sitkei传热

`Sitkei`传热是根据准则方程 $Nu = Re^{0.7}$ 导出, 适用于**直喷式**, **四冲程小型**柴油机。

$$
\alpha_{gas \to wall} = 1.294 \times 10^{-5} \left( 1 + b \right) \cdot
\frac{ \left(P \cdot c_m \right) ^ {0.7}} {T^{0.2} \cdot d_e^{0.3}}
$$

- $\alpha_{gas \to wall}$: 传热系数 (W/(m²·K))
- $d_e$: 当量直径, $d_e = \frac{2B \cdot h_{gap}}{B + 2h_{gap}}$
- $B$: 气缸直径 (m)
- $h_{gap}$: 活塞顶至气缸盖的距离 (m)
- $T$: 缸内温度 (K)
- $P$: 缸内压力 (Pa)
- $c_m$: 活塞平均速度 (m/s)
- $b$: 常数  
  直喷式燃烧室: $b=0 \sim 0.15$  
  涡流室式燃烧室: $b=0.15 \sim 0.25$  
  预燃室式燃烧室: $b=0.25 \sim 0.35$
