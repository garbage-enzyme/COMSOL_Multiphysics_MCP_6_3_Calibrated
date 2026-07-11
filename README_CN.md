# COMSOL MCP Server — 6.4+ ClientAPI 适配 Fork

[English](README.md) | 中文

[![GitHub stars](https://img.shields.io/github/stars/garbage-enzyme/COMSOL_Multiphysics_MCP_6_4_Calibrated?style=social)](https://github.com/garbage-enzyme/COMSOL_Multiphysics_MCP_6_4_Calibrated/stargazers)

> **本仓库是 [wjc9011/COMSOL_Multiphysics_MCP](https://github.com/wjc9011/COMSOL_Multiphysics_MCP) 的 Fork。**
> 本分支为 **COMSOL 6.4+ 及 MPh 1.3.1 standalone 模式**（`clientapi` 包装层）校准 MCP server 工具，并记录/使用 COMSOL 6.4+ 的求解器能力，例如 cuDSS GPU 加速直接求解器。上游代码面向直接的 `com.comsol.model.Model` API，在 standalone clientapi 下会运行时报错。

## 为什么要有这个 Fork

在 `mph.Client(cores=...)`（MPh 1.3+ standalone）下，`model.java` 返回的是 `com.comsol.clientapi.impl.ModelClient` —— 真实 model 外面的**包装层**。每一次 `component()` / `physics()` / `geom()` 调用返回的都是 `*Client` 类，其方法重载与上游代码所写的直接 `com.comsol.model.*` API 不同。结果：standalone clientapi 下大部分 geometry/physics/study/mesh 工具运行时失败。

本 Fork 修复了 `src/tools/` 下所有已知的 clientapi 不匹配，并补了两个缺失的工具。已通过 MCP 端到端验证：平行板电容器返回 **C = 1.8593794414 pF**，与理论值（1.8593794407 pF，误差 4 × 10⁻¹⁰ pF）一致。

> ⚠️ **来源说明：** 本 Fork 的代码改动由 AI 助手（opencode + glm-5.2）在人工指导下完成，随后通过 MCP 工具接口端到端验证。详细改动分解见 `git log`。

## 改了什么

所有修复都位于 `src/tools/`，针对 `clientapi` 包装类。按文件汇总：

### `model.py`
- `list_components`：用 `tags()` 遍历组件，而不是 int 索引 —— `ModelEntityListClient.get` 只接受 String tag。

### `geometry.py`
- 5 处 `len(geom.feature())` → `geom.feature().size()` —— clientapi 的 list 不支持 `len()`。
- 涉及 `add_block`、`add_cylinder`、`add_sphere`、`add_rectangle`、`boolean_difference`。

### `physics.py`
- 新增 helper `_first_component(jm)` 与 `_component_sdim(comp)` —— `getSDim()` 返回 int，而 physics `create` 需要的是 **String**。
- 所有 `comp.get(int)` → `tags()` 遍历。
- `physics().create(tag, type, sdim_string)` —— **三参数**，第三个是形如 `"3"` 的 String。两参数会报"物理场接口不支持空间维度: 0维"；第三参数传 int 会报 "No matching overloads"。
- `geometry_get_boundaries`：`getNboundary()` → `getNBoundaries()`，`getNdomain()` → `getNDomains()`（clientapi 中首字母大写）。
- `physics_add_electrostatics`：新增 `relpermittivity` + `domain_numbers` 参数。传入时自动创建 `ChargeConservation` feature + 材料节点 —— 必须这么做，因为 **COMSOL 6.3+/6.4 的 Electrostatics 默认 domain feature 是 `fsp1` (FreeSpace)，用真空 ε₀，忽略材料的 `relpermittivity`**。
- 新增通用工具 `physics_add_domain_feature`（ChargeConservation / LinearElasticMaterial / Solid 等）。

### `study.py`
- Study step type 用**完整名**（`Stationary` / `TimeDependent` / `Eigenfrequency` / `Frequency` / `Perturbation`），通过 `SHORT_TO_FULL` 映射。短名（`stat` / `time` / `eig` / `freq` / `pert`）在直接 Model API 下可用，但在 clientapi 下报 `Operation_cannot_be_created_in_this_context`。

### `mesh.py`
- 新增 `mesh_sequence_create` 工具。COMSOL **不会**自动创建 mesh 序列 —— 上游的 `mesh_create` 只能 run 已有序列。新工具做 `comp.mesh().create()` + `feature().create('FreeTet')` + `run()`，并通过 `getNumElem()` / `getNumVertex()`（clientapi，非 `getElement().size()`）报告单元数。

### 仓库清理
- 新增 `.gitignore`：`__pycache__/`、`*.pyc`、`opencode.json`（机器相关路径）、`knowledge_base/`（可重建）、`*.mph`。
- 不再跟踪 `opencode.json` 和 `knowledge_base/chroma.sqlite3` —— 二者均为本地专属 / 可重建。

## 验证

`test_e2e_cap.py` 与 `test_study_mesh.py` 是独立验证脚本（直接驱动 `mph.Client`，不走 MCP 层）。同一 recipe 也在重启 opencode 加载新代码后，通过 MCP 工具接口端到端复跑：

| 步骤 | MCP 工具 |
| --- | --- |
| 建模型 + 3D 组件 | `model_create` → `model_create_component(3D)` |
| 几何：10mm × 10mm × 1mm 块 | `geometry_create(3D)` → `geometry_add_block([0.01,0.01,0.001])` → `geometry_build` |
| 静电场，ε_r = 2.1 | `physics_add_electrostatics(relpermittivity=2.1, domain_numbers=[1])` |
| 边界条件：Ground @ z=0 (bnd 3)，V=1V @ z=1mm (bnd 4) | `physics_configure_boundary(Ground,[3])`，`physics_configure_boundary(ElectricPotential,[4],{V0:'1[V]'})` |
| 网格 | `mesh_sequence_create(FreeTet, build=True)` → 约 1663 单元 |
| 求解 | `study_create(Stationary)` → `study_solve` |
| 电容 | `results_global_evaluate('2*es.intWe/(1[V])^2','pF')` |

**结果：** `1.8593794414 pF`，理论值 `ε₀·ε_r·L²/d = 1.8593794407 pF` —— 误差 4 × 10⁻¹⁰ pF。

### 6.3+/6.4 clientapi 避坑（源码注释中有）

1. **Electrostatics `fsp1` FreeSpace 陷阱** —— 默认 domain feature 用真空 ε₀，忽略材料 `relpermittivity`。必须加一个 `ChargeConservation` feature（`materialType='from_mat'`）+ 一个材料节点（`propertyGroup('def').set('relpermittivity', ...)`）。
2. **Block 边界编号不是 1–6 ↔ −x/+x/−y/+y/−z/+z。** 对于 `Block size [0.01,0.01,0.001] pos [0,0,0]`：**bnd 3 = z=0 面，bnd 4 = z=0.001 面**；1/2/5/6 是侧面。用 `Box` selection（`condition='inside'`）按坐标确认。
3. **`Terminal` feature 的 `V0` 没正确约束电压**（V0=1V 时实测 ΔV ≈ 0.16 V）。电容验证请用 `ElectricPotential` 边界条件。
4. **表达式语法：** clientapi 下 `1[V]^2` 是语法错误 —— 必须写成 `(1[V])^2`。
5. **mph 1.3.1 的 `Model` 没有 `.study()` 方法** —— 用 `model.java.study('std1').run()`。

## 环境要求

- **COMSOL Multiphysics 6.4 或更新版本**。本 Fork 面向 COMSOL 6.4+ standalone clientapi，因为当前工作流可能调用 **cuDSS** GPU 加速直接求解器等 6.4+ 求解器能力。
- **Python 3.10+**（不要用 Windows Store 版）
- **Java 运行时** —— COMSOL 6.4 自带 Java 21；已验证环境下 JPype 可直接使用。更老 COMSOL/Java 组合不在本 Fork 重点范围内。
- **MPh 1.3.1**，加 `mcp`、`pydantic`。离线手册索引构建可选安装
  `pymupdf`；旧版语义 PDF 搜索还需要 `chromadb`、`sentence-transformers`。

## 安装

```bash
git clone https://github.com/garbage-enzyme/COMSOL_Multiphysics_MCP_6_4_Calibrated.git
cd COMSOL_Multiphysics_MCP_6_4_Calibrated
python -m pip install .
# 推荐：离线 lexical 手册索引（输出路径必须仅含 ASCII）
python -m pip install ".[manuals]"
python -m src.knowledge.lexical_manual build --index D:\comsol_docs_fts\manuals.sqlite3
# 可选：旧版 semantic PDF profile
python -m pip install ".[semantic-pdf]"
python scripts/build_knowledge_base.py
```

先启动 COMSOL Multiphysics（MCP 通过 MPh/JPype 桥接），然后把 MCP 客户端（opencode / Claude Desktop）指向 server：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "comsol": {
      "type": "local",
      "command": ["python", "-m", "src.server"]
    }
  }
}
```

## 与上游的关系

本 Fork 跟踪 `wjc9011/COMSOL_Multiphysics_MCP`，定位是 **6.4+ standalone clientapi 兼容 Fork**，不是通用功能 Fork。上游 README（原仓库的 `README.md`，本 Fork 保留为 `README_upstream.md` / `README_CN_upstream.md`）描述了更完整的功能集、知识库、5.x 工作流，本 Fork 原样继承。

如果你在 **6.4+ standalone** 下用上游工具报 `No matching overloads`、`Operation_cannot_be_created_in_this_context`、或 `'ComponentGeomListClient' object is not subscriptable` —— 请用本 Fork。最后一个错在本 Fork 已修复：`geometry_get_boundaries` 现在返回每个边界的 `normal`（法向）+ `center`（中心坐标）+ 整体 `bounding_box`（通过参数中点调 `faceNormal`/`faceX`/`edgeNormal`/`edgeX`），可直接判断哪个边界是哪个面（如 z=0 面法向 `[0,0,-1]`），无需手动建 `Box` selection。

## 许可证

继承上游许可证。详见原仓库。
