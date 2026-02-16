# COMSOL MCP 服务器

通过 AI 智能体自动化 COMSOL 多物理场仿真的 MCP 服务器。

[English](README.md) | 中文

## 项目目标

构建一个完整的 COMSOL MCP 服务器，使 AI 智能体（如 Claude、opencode）能够通过 MCP 协议执行多物理场仿真：

1. **模型管理** - 创建、加载、保存、版本控制
2. **几何构建** - 长方体、圆柱体、球体、布尔运算
3. **物理场配置** - 传热、流体流动、静电场、固体力学
4. **网格划分与求解** - 自动网格、稳态/瞬态研究
5. **结果可视化** - 表达式求值、导出图表
6. **知识库集成** - 内嵌指南 + PDF 语义搜索

## 系统要求

- **COMSOL Multiphysics**（5.x 或 6.x 版本）
- **Python 3.10+**（非 Windows Store 版本）
- **Java 运行时**（MPh/COMSOL 需要）

## 安装

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/comsol-mcp.git
cd comsol-mcp

# 安装依赖
python -m pip install -e .

# 测试服务器
python -m src.server
```

## 使用方式

### 方式 1：配合 opencode

在项目根目录创建 `opencode.json`：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "comsol": {
      "type": "local",
      "command": ["python", "-m", "src.server"],
      "enabled": true,
      "environment": {
        "HF_ENDPOINT": "https://hf-mirror.com"
      },
      "timeout": 30000
    }
  }
}
```

### 方式 2：配合 Claude Desktop

```json
{
  "mcpServers": {
    "comsol": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/comsol-mcp"
    }
  }
}
```

## 代码结构

```
comsol_mcp/
├── opencode.json                    # opencode MCP 服务器配置
├── pyproject.toml                   # Python 项目配置
├── README.md                        # 英文文档
├── README_CN.md                     # 中文文档（本文件）
│
├── src/
│   ├── server.py                    # MCP 服务器入口
│   ├── tools/
│   │   ├── session.py               # COMSOL 会话管理（启动/停止/状态）
│   │   ├── model.py                 # 模型增删改查 + 版本控制
│   │   ├── parameters.py            # 参数管理 + 参数化扫描
│   │   ├── geometry.py              # 几何创建（长方体/圆柱/球体）
│   │   ├── physics.py               # 物理场接口 + 边界条件
│   │   ├── mesh.py                  # 网格生成
│   │   ├── study.py                 # 研究创建 + 求解（同步/异步）
│   │   └── results.py               # 结果评估 + 导出
│   ├── resources/
│   │   └── model_resources.py       # MCP 资源（模型树、参数）
│   ├── knowledge/
│   │   ├── embedded.py              # 内嵌物理指南 + 故障排除
│   │   ├── retriever.py             # PDF 向量搜索检索器
│   │   └── pdf_processor.py         # PDF 分块 + 嵌入
│   ├── async_handler/
│   │   └── solver.py                # 异步求解与进度跟踪
│   └── utils/
│       └── versioning.py            # 模型版本路径管理
│
├── scripts/
│   └── build_knowledge_base.py      # 构建 PDF 向量数据库
│
├── client_script/                   # 独立建模脚本（示例）
│   ├── create_chip_tsv_final.py     # 示例：芯片热模型
│   ├── create_micromixer_auto.py    # 示例：流体流动仿真
│   ├── create_chip_thermal*.py      # 各种芯片热模型变体
│   ├── create_micromixer*.py        # 各种微混合器变体
│   ├── visualize_*.py               # 结果可视化脚本
│   ├── add_visualization.py         # 添加绘图组到模型
│   └── test_*.py                    # 集成测试
│
├── comsol_models/                   # 保存的模型（结构化）
│   ├── chip_tsv_thermal/
│   │   ├── chip_tsv_thermal_*.mph
│   │   └── chip_tsv_thermal_latest.mph
│   └── micromixer/
│       └── micromixer_*.mph
│
└── tests/
    └── test_basic.py                # 单元测试
```

## 可用工具（80+ 个）

### 会话管理 (4)

| 工具 | 描述 |
|------|------|
| `comsol_start` | 启动本地 COMSOL 客户端 |
| `comsol_connect` | 连接到远程服务器 |
| `comsol_disconnect` | 清除会话 |
| `comsol_status` | 获取会话信息 |

### 模型管理 (9)

| 工具 | 描述 |
|------|------|
| `model_load` | 加载 .mph 文件 |
| `model_create` | 创建空模型 |
| `model_save` | 保存到文件 |
| `model_save_version` | 保存带时间戳版本 |
| `model_list` | 列出已加载模型 |
| `model_set_current` | 设置当前活动模型 |
| `model_clone` | 克隆模型 |
| `model_remove` | 从内存移除模型 |
| `model_inspect` | 获取模型结构 |

### 参数 (5)

| 工具 | 描述 |
|------|------|
| `param_get` | 获取参数值 |
| `param_set` | 设置参数 |
| `param_list` | 列出所有参数 |
| `param_sweep_setup` | 设置参数化扫描 |
| `param_description` | 获取/设置参数描述 |

### 几何 (14)

| 工具 | 描述 |
|------|------|
| `geometry_list` | 列出几何序列 |
| `geometry_create` | 创建几何序列 |
| `geometry_add_feature` | 添加通用几何特征 |
| `geometry_add_block` | 添加长方体 |
| `geometry_add_cylinder` | 添加圆柱体 |
| `geometry_add_sphere` | 添加球体 |
| `geometry_add_rectangle` | 添加 2D 矩形 |
| `geometry_add_circle` | 添加 2D 圆形 |
| `geometry_boolean_union` | 布尔并集 |
| `geometry_boolean_difference` | 布尔差集 |
| `geometry_import` | 导入 CAD 文件 |
| `geometry_build` | 构建几何 |
| `geometry_list_features` | 列出几何特征 |
| `geometry_get_boundaries` | 获取边界编号 |

### 物理场 (16)

| 工具 | 描述 |
|------|------|
| `physics_list` | 列出物理场接口 |
| `physics_get_available` | 可用的物理场类型 |
| `physics_add` | 添加通用物理场 |
| `physics_add_electrostatics` | 添加静电场 |
| `physics_add_solid_mechanics` | 添加固体力学 |
| `physics_add_heat_transfer` | 添加传热 |
| `physics_add_laminar_flow` | 添加层流 |
| `physics_configure_boundary` | 配置边界条件 |
| `physics_set_material` | 分配材料 |
| `physics_list_features` | 列出物理场特征 |
| `physics_remove` | 移除物理场 |
| `multiphysics_add` | 添加多物理场耦合 |
| `physics_interactive_setup_heat` | 交互式传热边界设置 |
| `physics_setup_heat_boundaries` | 配置传热边界 |
| `physics_interactive_setup_flow` | 交互式流动边界设置 |
| `physics_boundary_selection` | 通用边界选择设置 |

### 网格 (3)

| 工具 | 描述 |
|------|------|
| `mesh_list` | 列出网格序列 |
| `mesh_create` | 生成网格 |
| `mesh_info` | 获取网格统计信息 |

### 研究与求解 (8)

| 工具 | 描述 |
|------|------|
| `study_list` | 列出研究 |
| `study_solve` | 同步求解 |
| `study_solve_async` | 后台求解 |
| `study_get_progress` | 获取求解进度 |
| `study_cancel` | 取消求解 |
| `study_wait` | 等待完成 |
| `solutions_list` | 列出解 |
| `datasets_list` | 列出数据集 |

### 结果 (9)

| 工具 | 描述 |
|------|------|
| `results_evaluate` | 求值表达式 |
| `results_global_evaluate` | 求值全局标量 |
| `results_inner_values` | 获取时间步值 |
| `results_outer_values` | 获取参数扫描值 |
| `results_export_data` | 导出数据 |
| `results_export_image` | 导出图表图像 |
| `results_exports_list` | 列出导出节点 |
| `results_plots_list` | 列出绘图节点 |

### 知识库 (8)

| 工具 | 描述 |
|------|------|
| `docs_get` | 获取文档 |
| `docs_list` | 列出可用文档 |
| `physics_get_guide` | 物理场快速指南 |
| `troubleshoot` | 故障排除帮助 |
| `modeling_best_practices` | 最佳实践 |
| `pdf_search` | 搜索 PDF 文档 |
| `pdf_search_status` | PDF 搜索状态 |
| `pdf_list_modules` | 列出 PDF 模块 |

## 示例案例

### 案例 1：带 TSV 的芯片热模型

带硅通孔（TSV）的硅芯片 3D 热分析。

**几何**：60×60×5 µm 芯片，5 µm 直径 TSV 孔，10×10 µm 热源

```python
# 关键步骤：
# 1. 创建芯片块和 TSV 圆柱
# 2. 布尔差集（从芯片减去 TSV）
# 3. 添加硅材料（k=130 W/m·K）
# 4. 添加传热物理场
# 5. 在顶部设置热通量，底部设置温度
# 6. 求解并评估温度分布
```

**脚本**：`client_script/create_chip_tsv_final.py`

**运行**：
```bash
cd /path/to/comsol-mcp
python client_script/create_chip_tsv_final.py
```

**结果**：在 1 MW/m² 热通量下相对于环境的温升

### 案例 2：微混合器流体流动

微流控通道中的 3D 层流仿真。

**几何**：600×100×50 µm 矩形通道

```python
# 关键步骤：
# 1. 创建矩形通道块
# 2. 添加水材料（ρ=1000 kg/m³, μ=0.001 Pa·s）
# 3. 添加层流物理场
# 4. 设置入口速度（1 mm/s），出口压力
# 5. 添加稀物质传递用于混合
# 6. 求解并评估速度分布
```

**脚本**：`client_script/create_micromixer_auto.py`

**运行**：
```bash
cd /path/to/comsol-mcp
python client_script/create_micromixer_auto.py
```

**结果**：速度分布、浓度混合剖面

## 模型版本控制

模型按结构化路径保存：

```
./comsol_models/{模型名称}/{模型名称}_{时间戳}.mph
./comsol_models/{模型名称}/{模型名称}_latest.mph
```

示例：
```
./comsol_models/chip_tsv_thermal/chip_tsv_thermal_20260216_140514.mph
./comsol_models/chip_tsv_thermal/chip_tsv_thermal_latest.mph
```

## 关键技术发现

### 1. mph 库 API 模式

```python
# 通过属性访问 Java 模型（不是方法调用）
jm = model.java  # 不是 model.java()

# 创建组件时使用 True 标志
comp = jm.component().create('comp1', True)

# 创建 3D 几何
geom = comp.geom().create('geom1', 3)

# 创建物理场时需要引用几何
physics = comp.physics().create('spf', 'LaminarFlow', 'geom1')

# 带选择的边界条件
bc = physics.create('inl1', 'InletBoundary')
bc.selection().set([1, 2, 3])
bc.set('U0', '1[mm/s]')
```

### 2. 边界条件属性名称

| 物理场 | 条件 | 属性 |
|--------|------|------|
| 传热 | HeatFluxBoundary | `q0` |
| 传热 | TemperatureBoundary | `T0` |
| 传热 | ConvectiveHeatFlux | `h`, `Text` |
| 层流 | InletBoundary | `U0`, `NormalInflowVelocity` |
| 层流 | OutletBoundary | `p0` |

### 3. 客户端会话限制

mph 库创建单例 COMSOL 客户端。每个 Python 进程只能存在一个 Client：

```python
# 在 session.py 中处理 - 客户端保持活跃，模型被清除
client.clear()  # 清除模型而不是完全断开连接
```

### 4. 离线嵌入模型

PDF 搜索支持使用本地 HuggingFace 缓存的离线操作：

```bash
# 为中国用户设置镜像
export HF_ENDPOINT=https://hf-mirror.com
```

## 开发状态

| 阶段 | 描述 | 状态 |
|------|------|------|
| 1 | 基础框架 + 会话 + 模型 | 已完成 |
| 2 | 参数 + 求解 + 结果 | 已完成 |
| 3 | 几何 + 物理场 + 网格 | 已完成 |
| 4 | 内嵌知识 + 工具文档 | 已完成 |
| 5 | PDF 向量检索 | 已完成 |
| 6 | 集成测试 | 进行中 |

## 下一步计划

1. **完成阶段 6** - 完整集成测试与正确的边界条件
2. **可视化导出** - 从绘图组生成 PNG 图像
3. **LSP 警告** - 修复 physics.py 中的类型提示
4. **更多示例** - 添加静电场、固体力学案例
5. **错误处理** - 改进错误消息和恢复机制

## 构建 PDF 知识库

```bash
# 安装额外依赖
pip install pymupdf chromadb sentence-transformers

# 构建知识库
python scripts/build_knowledge_base.py

# 检查状态
python scripts/build_knowledge_base.py --status
```

## 资源

| URI | 描述 |
|-----|------|
| `comsol://session/info` | 会话信息 |
| `comsol://model/{name}/tree` | 模型树结构 |
| `comsol://model/{name}/parameters` | 模型参数 |
| `comsol://model/{name}/physics` | 物理场接口 |

## 许可证

MIT
