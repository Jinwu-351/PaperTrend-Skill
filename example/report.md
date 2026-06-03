# 3D Gaussian Splatting 大场景重建趋势报告

**分析时间范围**: 2023 — 2026
**数据来源**: 62 篇论文（12 篇核心 + 50 篇补充），通过 arXiv、Semantic Scholar、OpenAlex、AlphaXiv 多源检索
**方法说明**: 基于 BM25 检索与 RRF 多路融合筛选
**质量分布**: T1 (同行评议) 13 篇 | T2 (预印本) 41 篇 | T3 (待核实) 8 篇

> ⚠️ 部分趋势来自预印本研究，尚待同行评议验证。

---

## 1. 领域概览

3D Gaussian Splatting (3DGS) 自 2023 年 SIGGRAPH 首次提出以来，在两年多时间里从一项新颖的 3D 表示技术迅速演变为 3D 视觉与计算机图形学的主流方法，已成为基于图像的 3D 重建与渲染方向增长最快的研究方向之一。

- **核心优势**: 3DGS 通过显式高斯原语表示场景，结合可微分光栅化实现新视角合成，在不依赖神经网络推理的前提下达到实渲染速度与高保真质量 [2]。相比 NeRF，3DGS 在重建精度和效率上均有显著提升，PSNR 提高约 10-13 dB，SSIM 提高 0.3-0.4，LPIPS 降低约 0.1 [5]。
- **权威综述涌现**: 领域已进入体系化阶段。Fei 等人 [2] 在 IEEE TVCG 发表首篇综述，Bao 等人 [12] 在 IEEE TCSVT 发表交叉视角综述，另有 3DGS.zip [Wiley 2025] 等压缩专项综述，表明该领域已形成从基础理论到工程优化的知识体系。
- **应用场景扩展**: 从初始的受限小场景新视角合成，迅速扩展至城市场景数字孪生 [5][18]、自动驾驶场景重建 [10][21]、大规模航拍建模 [3][26]、科学可视化 [8]、室内导航 [31] 等多个领域。

---

## 2. 主要研究方向与分类

> **分类标准说明**: 以下聚类基于论文摘要中的主要方法关键词。一篇论文可能被归入多个方向。计数为非互斥的近似值。（基于摘要关键词匹配的人工聚类，不同分类标准可能导致不同计数）

通过对 62 篇论文的系统聚类，可将当前 3DGS 大场景重建研究划分为以下方向：

### 2.1 大场景/城市场景重建（约 15-20 篇 | 热度: ★★★★★）

**分类标准**: 摘要中明确提及"large-scale"、"urban"、"unbounded"、"aerial"等场景描述词。

**核心挑战**: 大规模场景面临数据初始化困难、显存开销大、多视角几何一致性难以保证、渲染效率随场景规模下降等问题 [9]。

**关键进展**:
- **分块/分区策略**: LargeSceneGaussian (LSG) [9] 提出基于 K-Means 的场景分区方法，将大规模场景划分为独立子块并行训练后无缝合并，显存降低 15%，训练加速 10%；BlockGaussian [45] 采用自适应分块策略提升大规模场景新视角合成效率；HUG [30] 提出层次化城市场景分块重建框架。
- **城市场景实证评估**: Xu 等人 [5] 首次将 3DGS 应用于城市核心区的卫星影像重建，证明其在多时段光照条件下指标波动低于 2%；Yan 等人 [6] 系统评估了多种 GS 方法在城市场景中的可扩展性和几何精度。
- **航拍大场景**: AGS [3] 提出针对航拍大场景的数据分块方法和 Ray-Gaussian 交叉求交，首次证明 3DGS 在大场景几何精度上可与传统 MVS 方法匹敌；GauU-Scene [4] 构建了超过 1.5 平方公里的基准数据集。
- **无界场景**: Unbounded-GS [28] 提出混合表示方法扩展 3DGS 至无界大场景重建；Holistic [20] 提出混合高斯分块的统一大场景重建框架。

### 2.2 Feed-Forward 快速重建（约 10-15 篇 | 热度: ★★★★）

**分类标准**: 摘要中提及"feed-forward"、"real-time reconstruction"、"pose-free"等关键词，强调无需逐场景优化的快速推理能力。

**核心挑战**: 传统 3DGS 需要逐场景迭代优化，无法实时推理；feed-forward 方法需要在稀疏视角、缺乏相机外参的条件下实现高质量重建。

**关键进展**:
- **驾驶场景 feed-forward**: DrivingForward [10] 联合训练位姿网络、深度网络和高斯网络，在 nuScenes 数据集上实现从灵活环绕视角的前馈重建，无需深度真值和相机外参；SparseSplat [16] 提出像素未对齐预测的实用化 feed-forward 方法。
- **通用 feed-forward 框架**: GS-LRM [19] 提出 3DGS 大型重建模型；AirSplat [15] 引入对齐与评级机制提升鲁棒性；AnchorSplat [13] 融合 3D 几何先验实现前馈预测。
- **无位姿方法**: PF3plat [46] 提出无需相机位姿的 feed-forward 3DGS 方法；COLMAP-Free 3DGS [22] 完全摆脱 COLMAP 位姿估计流程。
- **2026 年新方向**: VolSplat [36] 提出体素对齐预测重新思考 feed-forward 架构；ForeSplat [29] 引入优化感知预视机制。

### 2.3 SLAM 与实时定位建图（约 6-8 篇 | 热度: ★★★）

**分类标准**: 摘要中明确提及"SLAM"、"localization"、"mapping"或同时包含实时重建与位姿估计。

**核心挑战**: 3DGS 需要已知相机位姿，而 SLAM 需要在线估计位姿并增量构建地图，二者融合面临实时性约束和累积误差问题。

**关键进展**:
- **视觉 SLAM 集成**: GS-SLAM [37] 首次将 3DGS 应用于稠密视觉 SLAM；SEGS-SLAM [44] 引入结构增强和外观嵌入提升 SLAM 精度；RTGS [38] 通过多级冗余压缩实现实时 3DGS SLAM。
- **动态/特殊场景**: Flow4DGS-SLAM [17] 将光流约束引入 4D 高斯 SLAM；EndoFlow-SLAM [25] 面向内窥镜场景提出光流约束的 GS SLAM。
- **置信度建模**: ConfidentSplat [34] 提出置信度加权的深度融合方法提升 SLAM 精度。

### 2.4 压缩与紧凑表示（约 5-8 篇 | 热度: ★★★）

**分类标准**: 摘要中提及"compression"、"compact"、"storage"、"coding"或"memory reduction"等关键词。

**核心挑战**: 3DGS 模型文件通常达数百 MB，大规模场景下存储和传输成本高。

**关键进展**:
- **编码压缩**: CodecSplat [40] 提出潜在编码实现超紧凑 feed-forward 3DGS；前馈压缩方法 [23] 利用长上下文建模实现 3DGS 压缩。
- **紧凑优化**: DashGaussian [1] 提出动态优化复杂度调度方案，平均加速 45.7% 同时保持渲染质量；Steepest Descent Density Control [39] 通过最速下降密度控制实现紧凑表示。

### 2.5 多 GPU 分布式训练（约 2-3 篇 | 热度: ★★）

**分类标准**: 摘要中明确提及"multi-GPU"、"distributed"、"HPC"或可扩展性。

**核心挑战**: 超大规模场景（如千万级高斯）超出单 GPU 显存容量。

**关键进展**:
- **分布式训练**: Distributed 3DGS [8] 基于 Grendel-GS 后端实现多 GPU 分布式训练，在 Kingsnake 数据集上 4 GPU 实现 5.6 倍加速，成功训练 1800 万高斯的 Miranda 数据集（单 A100 不可行）。
- **负载均衡**: LoBE-GS [42] 提出负载均衡的大场景 3DGS 方法。

---

## 3. 代表性论文一览

| 方向 | 代表性论文 (第一作者, 年份) | 核心贡献 |
|------|--------------------------|---------|
| **大场景/城市场景重建** | Ge et al. (2025) LargeSceneGaussian [9] / Xu et al. (2025) 城市卫星影像 [5] | 分块策略/城市场景实证，显存降15%/多时段鲁棒性<2% |
| **大场景/城市场景重建** | Wu et al. (2024) AGS [3] / Li et al. (2024) Unbounded-GS [28] | 航拍数据分块+Ray-Gaussian/混合表示扩展无界场景 |
| **Feed-Forward 快速重建** | Tian et al. (2024) DrivingForward [10] / Zhang et al. (2024) GS-LRM [19] | 驾驶场景前馈重建/大型重建模型 |
| **Feed-Forward 快速重建** | Zhang et al. (2026) SparseSplat [16] / Hong et al. (2025) PF3plat [46] | 像素未对齐预测/无位姿前馈方法 |
| **SLAM 与定位建图** | Chi et al. (2024) GS-SLAM [37] / Wang et al. (2026) Flow4DGS-SLAM [17] | 首将3DGS用于稠密SLAM/光流引导4D GS SLAM |
| **压缩与紧凑表示** | Chen et al. (2025) DashGaussian [1] / Yu et al. (2026) CodecSplat [40] | 动态复杂度调度/超紧凑潜在编码 |
| **多 GPU 分布式训练** | Han et al. (2025) Distributed 3DGS [8] | 4GPU 5.6x加速，18M高斯训练 |
| **质量与抗锯齿** | Yu et al. (2024) Mip-Splatting [7] / Yan et al. (2024) Multi-Scale [41] | 3D频域平滑+2D Mip滤波/多尺度抗锯齿 |

---

## 4. 技术趋势与演变

### 4.1 从"能不能用"到"好不好用"的演进

**阶段一 (2023 中期-2024) — 基础确立期**: Kerbl 等人提出原始 3DGS 方法后，研究迅速聚焦于基础改进：Mip-Splatting [7] 解决多尺度渲染伪影问题，Multi-Scale 3DGS [41] 提供抗别名渲染能力，Compressed 3DGS [33] 首次探索压缩方向。GS-SLAM [37] 和 COLMAP-Free 3DGS [22] 等开始摆脱对已知位姿的依赖。大场景方面，VastGaussian [24] 首次探索大规模场景 3DGS 重建。

**阶段二 (2024 中期-2025) — 质量与效率并重期**: 研究从"能否工作"转向"如何工作得更好"。FreGS [11] 提出渐进频率正则化解决高斯膨胀问题；DashGaussian [1] 实现 45.7% 加速；LargeSceneGaussian [9] 通过分块策略解决大规模场景的显存瓶颈；DrivingForward [10] 在驾驶场景实现前馈重建。城市场景方向，Xu 等人 [5] 和 Yan 等人 [6] 分别验证了 3DGS 在城市数字孪生中的可行性。

**阶段三 (2025 中期-2026) — 系统化与应用深化期**: 多篇权威综述 [2][12] 标志领域进入体系化阶段。技术路线分化为三大方向：(a) feed-forward 方法快速成熟，从场景特定的 DrivingForward [10] 发展到通用的 SparseSplat [16]、VolSplat [36]、AnchorSplat [13]；(b) SLAM 集成从概念验证 (GS-SLAM [37]) 走向实用化 (RTGS [38]、SEGS-SLAM [44]、Flow4DGS-SLAM [17])；(c) 分布式训练突破单 GPU 限制 [8]，为城市场景和 HPC 应用打开空间。

### 4.2 关键技术演进路线

| 技术维度 | 早期 (2023-2024) | 中期 (2024-2025) | 近期 (2025-2026) |
|---------|----------------|----------------|----------------|
| **场景规模** | 受限小场景 | 大场景分块 [9][24] | 城市级/无界 [5][28][30] |
| **优化方式** | 逐场景优化 | 频率正则化 [11] | 动态调度 [1][39] |
| **推理模式** | 迭代优化 | 场景特定前馈 [10][19] | 通用前馈 [16][36][46] |
| **存储表示** | 原始高斯 | 压缩编码 [33] | 超紧凑编码 [40][23] |
| **定位建图** | 需已知位姿 [22] | GS-SLAM [37] | 实时/多模态 [17][38][44] |
| **计算扩展性** | 单 GPU | 多视角优化 [9] | 多 GPU 分布式 [8][42] |

---

## 5. 热门研究方向分析

### 最受关注（论文数量最多）

1. **大场景/城市场景重建**（约 15-20 篇）—— 作为本报告核心关注方向，3DGS 在城市数字孪生 [5]、航拍重建 [3][26]、无界场景 [28] 等领域取得突破性进展，多篇论文验证了 3DGS 在大场景中的几何精度和渲染质量优势。
2. **Feed-Forward 快速重建**（约 10-15 篇）—— 2025-2026 年呈爆发式增长，从驾驶场景 [10] 扩展到通用框架 [16][36]，再到无位姿方法 [46]，代表了从"优化"到"推理"的范式转移。
3. **SLAM 与实时定位建图**（约 6-8 篇）—— 3DGS 与 SLAM 的结合从概念验证 [37] 走向实时实用 [38]，并拓展至内窥镜 [25]、4D 动态 [17] 等特殊场景。

### 增长最快的新兴方向

1. **Feed-Forward 3DGS 的泛化能力** —— SparseSplat [16]、VolSplat [36]、AirSplat [15] 等在 2026 年密集出现，从像素对齐转向体素对齐、引入对齐评级机制，代表了该子方向的快速迭代。
2. **多模态/多源融合** —— MuDG [14] 融合多模态扩散模型与高斯，Neural-MMGS [32] 实现多模态神经高斯，表明 3DGS 正与更多数据模态结合。
3. **分布式/可扩展 3DGS** —— 多 GPU 训练 [8] 和负载均衡方法 [42] 在 2025-2026 年涌现，为超大规模场景打开新空间。
4. **3DGS 压缩标准化** —— 从单篇压缩方法 [33] 发展为系统性的 3DGS.zip 综述，再到 CodecSplat [40] 的潜在编码，压缩正从研究问题走向工程标准。

---

## 6. 应用前景

| 应用场景 | 潜力评估 | 支撑论文 | 技术就绪度 |
|---------|---------|---------|-----------|
| **城市数字孪生** | ★★★★ | [5][6][18][30][43] | 中期：已验证可行性，几何精度接近传统方法 |
| **自动驾驶场景重建** | ★★★★ | [10][21][27] | 中后期：DrivingForward 等实现前馈重建，需更多实车验证 |
| **航拍/卫星影像重建** | ★★★ | [3][26][4] | 中期：AGS 等方法证明几何精度，数据分块方案成熟 |
| **SLAM/室内导航** | ★★★ | [37][38][44][31] | 初期-中期：概念验证到实时化过渡 |
| **科学可视化/HPC** | ★★ | [8] | 初期：多 GPU 方案初步可行，生态仍在建设 |

---

## 7. 未来展望

基于本报告分析的 62 篇论文趋势，未来可能出现以下发展方向：

1. **统一的大场景 3DGS 框架**: 当前大场景方法多为分块式 [9][45] 或层次化 [30] 策略，缺乏统一的可扩展架构 [推断]。预计未来 1-2 年会出现类似"大模型"的统一 3DGS 框架，支持从室内到城市场景的自适应重建。
2. **Feed-Forward 3DGS 的零样本泛化**: SparseSplat [16]、VolSplat [36] 等 feed-forward 方法正在快速逼近"输入即输出"的理想状态，但跨域泛化能力仍需提升 [推断]。结合大语言模型或视觉基础模型 [35] 可能是突破方向。
3. **3DGS 实时 SLAM 的工业应用**: GS-SLAM [37]、RTGS [38]、SEGS-SLAM [44] 等将 3DGS 与 SLAM 深度集成，有望在无人机自主导航 [31]、内窥镜导航 [25] 等场景中率先落地。
4. **3DGS 压缩与传输标准化**: SIGGRAPH 2025 已讨论标准化议题 [推断]。随着 3DGS 被越来越多地用作 3D 内容格式（"3D 的 JPEG"），建立统一的压缩和传输标准将成为产业界和学术界的共同需求。
5. **物理一致的动态 3DGS**: DENSER [21][27] 等探索动态城市场景重建，但物理约束（如重力、运动学）在 3DGS 中的融入仍不充分 [推断]。未来可能发展出物理感知的 3DGS 变体。

---

## 8. 现存挑战

- **显存与存储瓶颈**: 大场景 3DGS 模型动辄数 GB，压缩方法虽有效但尚无统一标准。LargeSceneGaussian [9] 将显存降低 15%，但城市场景级重建仍面临显著存储压力。
- **几何精度与渲染质量的权衡**: AGS [3] 首次证明 3DGS 在几何精度上可与传统 MVS 方法匹敌，但 Yan 等人 [6] 的系统评估表明，不同方法在几何精度和渲染质量之间存在明显 trade-off。
- **Feed-Forward 的泛化能力**: 当前 feed-forward 方法多在特定数据集（如 nuScenes）上训练 [10]，跨数据集、跨场景的零样本泛化能力尚未充分验证 [推断]。
- **SLAM 的累积误差**: 3DGS SLAM 在实时重建方面取得进展 [37][38]，但长序列运行中的累积误差和漂移问题仍是核心挑战 [推断]。

### 8.1 停滞或衰退的研究方向

- **纯逐场景优化的小场景重建**: 自 2024 年中期以来，针对受限小场景的纯 3DGS 优化论文数量呈现明显下降趋势，研究热点已转向 feed-forward 推理和大场景扩展。可能原因：(a) 原始 3DGS 在小场景上的质量已接近上限，进一步优化的边际收益递减；(b) feed-forward 方法的推理效率优势使其更具实用价值 [归纳]。
- **单纯的压缩率优化**: 随着 3DGS.zip 综述的系统总结和 CodecSplat [40] 等方法的出现，单纯追求压缩率的研究正在减少，转而关注压缩-质量联合优化和标准化。

### 8.2 为何尚未成为主流

尽管 3DGS 在学术界发展迅速，但与深度学习/Transformer 那样成为工业界主流标准仍有差距：

- **理论瓶颈**: 3DGS 的本质是离散高斯原语的集合，其数学表达与连续物理场景之间存在语义鸿沟 [推断]。相比 NeRF 的连续隐式表示，3DGS 的显式表示在几何一致性上仍有不足，这在大规模场景中尤为突出 [6]。
- **工程挑战**: 城市场景级 3DGS 模型的文件大小、渲染硬件要求、以及多时段光照一致性等问题尚未彻底解决。多 GPU 训练虽突破了显存限制 [8]，但部署门槛仍然较高。
- **生态因素**: 3DGS 缺乏统一的格式标准和成熟的工具链。虽然 SIGGRAPH 2025 已开始讨论标准化，但从研究到工业落地仍需完整的工具生态（建模软件、查看器、压缩工具、传输协议等）。

---

*本报告的事实性描述（标注 [N] 的引用）来源于引用文献的论文摘要。趋势分析、方法聚类与未来方向为作者基于文献证据的综合归纳与推断。推断性内容已标注 [推断]。部分趋势来自预印本研究，尚待同行评议验证。报告中的论文数量统计为基于摘要关键词的近似分类，不同分类标准可能导致不同计数。*


---

## 参考文献

[1] Chen, Youyu, Jiang, Junjun, Jiang, Kui, 等. DashGaussian: Optimizing 3D Gaussian Splatting in 200 Seconds[J]. arXiv preprint, 2025. https://arxiv.org/abs/2503.18402.

[2] Ben Fei, Jingyi Xu, Rui Zhang, 等. 3D Gaussian Splatting as a New Era: A Survey[J]. IEEE Transactions on Visualization and Computer Graphics, 2024.

[3] Wu, YuanZheng, Liu, Jin, Ji, Shunping. 3D Gaussian Splatting for Large-scale Surface Reconstruction from Aerial Images[J]. arXiv preprint, 2024. https://arxiv.org/abs/2409.00381.

[4] Butian Xiong, Zhuo Li, Zhen Li. GauU-Scene: A Scene Reconstruction Benchmark on Large Scale 3D Reconstruction Dataset Using Gaussian Splatting[J]. arXiv (Cornell University), 2024.

[5] Hanqing Xu, Lingfei Ma, Haiyan Guan, 等. Large-Scale Urban Scene Reconstruction Using 3D Gaussian Splatting and Satellite Imagery[J]. openalex, 2025.

[6] Ziyang Yan, Mengrui Yin, Yu Shao, 等. Evaluating 3D Gaussian Splatting for Urban Scene Reconstruction[J]. The international archives of the photogrammetry, remote sensing and spatial information sciences/International archives of the photogrammetry, remote sensing and spatial information sciences, 2025.

[7] Zehao Yu, Anpei Chen, Binbin Huang, 等. Mip-Splatting: Alias-Free 3D Gaussian Splatting[J]. openalex, 2024.

[8] Han, Mengjiao, Sewell, Andres, Insley, Joseph, 等. Toward Distributed 3D Gaussian Splatting for High-Resolution Isosurface Visualization[J]. arXiv preprint, 2025. https://arxiv.org/abs/2509.05216.

[9] Yongxin Ge, Junqi Liao, Li Li, 等. LargeSceneGaussian: High-Efficiency 3D Gaussian Splatting for Large-Scale Scene Reconstruction[J]. openalex, 2025.

[10] Tian, Qijian, Tan, Xin, Xie, Yuan, 等. DrivingForward: Feed-forward 3D Gaussian Splatting for Driving Scene Reconstruction from Flexible Surround-view Input[J]. arXiv preprint, 2024. https://arxiv.org/abs/2409.12753.

[11] Zhang, Jiahui, Zhan, Fangneng, Xu, Muyu, 等. FreGS: 3D Gaussian Splatting with Progressive Frequency Regularization[J]. arXiv preprint, 2024. https://arxiv.org/abs/2403.06908.

[12] Yanqi Bao, Tianyu Ding, Jing Huo, 等. 3D Gaussian Splatting: Survey, Technologies, Challenges, and Opportunities[J]. IEEE Transactions on Circuits and Systems for Video Technology, 2025.

[13] Zhang, Xiaoxue, Zheng, Xiaoxu, Yin, Yixuan, 等. AnchorSplat: Feed-Forward 3D Gaussian Splatting with 3D Geometric Priors[J]. arXiv preprint, 2026. https://arxiv.org/abs/2604.07053.

[14] Zou, Yingshuang, Ding, Yikang, Zhang, Chuanrui, 等. MuDG: Taming Multi-modal Diffusion with Gaussian Splatting for Urban Scene Reconstruction[J]. arXiv preprint, 2025. https://arxiv.org/abs/2503.10604.

[15] Minh-Quan Viet Bui, Jaeho Moon Jaeho Moon, Munchurl Kim. AirSplat: Alignment and Rating for Robust Feed-Forward 3D Gaussian Splatting[J]. ArXiv.org, 2026.

[16] Zhang, Zicheng, Meng, Xiangting, Wu, Ke, 等. SparseSplat: Towards Applicable Feed-Forward 3D Gaussian Splatting with Pixel-Unaligned Prediction[J]. arXiv preprint, 2026. https://arxiv.org/abs/2604.03069.

[17] Wang, Yunsong, Lee, Gim Hee. Flow4DGS-SLAM: Optical Flow-Guided 4D Gaussian Splatting SLAM[J]. arXiv preprint, 2026. https://arxiv.org/abs/2604.22339.

[18] Kyle Gao, Dening Lu, Hongjie He, 等. Enhanced 3-D Urban Scene Reconstruction and Point Cloud Densification Using Gaussian Splatting and Google Earth Imagery[J]. IEEE Transactions on Geoscience and Remote Sensing, 2025.

[19] Zhang, Kai, Bi, Sai, Tan, Hao, 等. GS-LRM: Large Reconstruction Model for 3D Gaussian Splatting[J]. arXiv preprint, 2024. https://arxiv.org/abs/2404.19702.

[20] Liu, Chuandong, Wang, Huijiao, Yu, Lei, 等. Holistic Large-Scale Scene Reconstruction via Mixed Gaussian Splatting[J]. arXiv preprint, 2025. https://arxiv.org/abs/2505.23280.

[21] Mahmud A. Mohamad, Gamal Elghazaly, Arthur Hubert, 等. DENSER: 3D Gaussian Splatting for Scene Reconstruction of Dynamic Urban Environments[J]. openalex, 2025.

[22] Yang Fu, Xiaolong Wang, Sifei Liu, 等. COLMAP-Free 3D Gaussian Splatting[J]. openalex, 2024.

[23] Zhening Liu, Rui Song, Yushi Huang, 等. Feed-Forward 3D Gaussian Splatting Compression with Long-Context Modeling[J]. ArXiv.org, 2025.

[24] Lin, Jiaqi, Li, Zhihao, Tang, Xiao, 等. VastGaussian: Vast 3D Gaussians for Large Scene Reconstruction[J]. arXiv preprint, 2024. https://arxiv.org/abs/2402.17427.

[25] Wu, Taoyu, Miao, Yiyi, Li, Zhuoxiao, 等. EndoFlow-SLAM: Real-Time Endoscopic SLAM with Flow-Constrained Gaussian Splatting[J]. arXiv preprint, 2025. https://arxiv.org/abs/2506.21420.

[26] Qiulin Sun, Wei Lai, Yixian Li, 等. Gaussian Splatting for Large‐Scale Aerial Scene Reconstruction From Ultra‐High‐Resolution Images[J]. Computer Graphics Forum, 2025.

[27] Mohamad, Mahmud A., Elghazaly, Gamal, Hubert, Arthur, 等. DENSER: 3D Gaussians Splatting for Scene Reconstruction of Dynamic Urban Environments[J]. arXiv preprint, 2024. https://arxiv.org/abs/2409.10041.

[28] Wanzhang Li, Fukun Yin, Wen Liu, 等. Unbounded-GS: Extending 3D Gaussian Splatting With Hybrid Representation for Unbounded Large-Scale Scene Reconstruction[J]. IEEE Robotics and Automation Letters, 2024.

[29] Yuke Li, Weihang Liu, Cheng Zhang, 等. ForeSplat: Optimization-Aware Foresight for Feed-Forward 3D Gaussian Splatting[J]. arXiv (Cornell University), 2026.

[30] Su, Mai, Wang, Zhongtao, Au, Huishan, 等. HUG: Hierarchical Urban Gaussian Splatting with Block-Based Reconstruction for Large-Scale Aerial Scenes[J]. arXiv preprint, 2025. https://arxiv.org/abs/2504.16606.

[31] Liu, Jiahang, Duan, Yuanxing, Zhang, Jiazhao, 等. NavGSim: High-Fidelity Gaussian Splatting Simulator for Large-Scale Navigation[J]. arXiv preprint, 2026. https://arxiv.org/abs/2603.15186.

[32] Sitian Shen, Georgi Pramatarov, Yifu Tao, 等. Neural-MMGS: Multi-modal Neural Gaussian Splats for Large-Scale Scene Reconstruction[J]. ArXiv.org, 2025.

[33] Simon Niedermayr, Josef Stumpfegger, Rüdiger Westermann. Compressed 3D Gaussian Splatting for Accelerated Novel View Synthesis[J]. openalex, 2024.

[34] Dufera, Amanuel T., Cai, Yuan-Li. ConfidentSplat: Confidence-Weighted Depth Fusion for Accurate 3D Gaussian Splatting SLAM[J]. arXiv preprint, 2025. https://arxiv.org/abs/2509.16863.

[35] Mingwei Xing, Xinliang Wang, Yifeng Shi. AdaptSplat: Adapting Vision Foundation Models for Feed-Forward 3D Gaussian Splatting[J]. ArXiv.org, 2026.

[36] Wang, Weijie, Chen, Yeqing, Zhang, Zeyu, 等. VolSplat: Rethinking Feed-Forward 3D Gaussian Splatting with Voxel-Aligned Prediction[J]. arXiv preprint, 2026. https://arxiv.org/abs/2509.19297.

[37] Yan Chi, Delin Qu, Dan Xu, 等. GS-SLAM: Dense Visual SLAM with 3D Gaussian Splatting[J]. openalex, 2024.

[38] Li, Leshu, Qin, Jiayin, Peng, Jie, 等. RTGS: Real-Time 3D Gaussian Splatting SLAM via Multi-Level Redundancy Reduction[J]. arXiv preprint, 2025. https://arxiv.org/abs/2510.06644.

[39] Wang, Peihao, Wang, Yuehao, Wang, Dilin, 等. Steepest Descent Density Control for Compact 3D Gaussian Splatting[J]. arXiv preprint, 2025. https://arxiv.org/abs/2505.05587.

[40] Pengpeng Yu, Runqing Jiang, Qi S. Zhang, 等. CodecSplat: Ultra-Compact Latent Coding for Feed-Forward 3D Gaussian Splatting[J]. arXiv (Cornell University), 2026.

[41] Zhiwen Yan, Weng Fei Low, Yu Chen, 等. Multi-Scale 3D Gaussian Splatting for Anti-Aliased Rendering[J]. openalex, 2024.

[42] Hung, Sheng-Hsiang, Yen, Ting-Yu, Sun, Wei-Fang, 等. LoBE-GS: Load-Balanced and Efficient 3D Gaussian Splatting for Large-Scale Scene Reconstruction[J]. arXiv preprint, 2026. https://arxiv.org/abs/2510.01767.

[43] Gao, Yuanyuan, Li, Hao, Chen, Jiaqi, 等. CityGS-X: A Scalable Architecture for Efficient and Geometrically Accurate Large-Scale Scene Reconstruction[J]. arXiv preprint, 2025. https://arxiv.org/abs/2503.23044.

[44] Wen, Tianci, Liu, Zhiang, Fang, Yongchun. SEGS-SLAM: Structure-enhanced 3D Gaussian Splatting SLAM with Appearance Embedding[J]. arXiv preprint, 2025. https://arxiv.org/abs/2501.05242.

[45] Wu, Yongchang, Qi, Zipeng, Shi, Zhenwei, 等. BlockGaussian: Efficient Large-Scale Scene Novel View Synthesis via Adaptive Block-Based Gaussian Splatting[J]. arXiv preprint, 2025. https://arxiv.org/abs/2504.09048.

[46] Hong, Sunghwan, Jung, Jaewoo, Shin, Heeseong, 等. PF3plat: Pose-Free Feed-Forward 3D Gaussian Splatting[J]. arXiv preprint, 2025. https://arxiv.org/abs/2410.22128.
