# MLJ Factorio Mods

这是一个 Factorio Lua 模组工作区。每个模组都以独立目录维护源码，
共享根目录的 `pack_mods.py` 进行发现、校验和打包。

## 当前模组

| 目录 | 模组 | 说明 |
|------|------|------|
| `DynamicInventory/` | DynamicInventory | 按玩家设置动态调整背包容量的运行时模组 |
| `expend-toolbar/` | expend-toolbar | 创建可移动自定义工具栏，并显示当前视图的物品数量 |
| `py_quick_start/` | py_quick_start | 给 Pyanodons 开局提供装备和机器人等物品的运行时模组 |
| `quality-cycler/` | quality-cycler | 调整蓝图、蓝图册和绿图中品质的运行时模组 |
| `section-autocraft/` | section-autocraft | 根据物流编组自动安排手搓的模组 |
| `ups_saving_quality_ships/` | ups_saving_quality_ships | 用品质枢纽模拟多艘同款飞船以降低 UPS 压力的 Space Age 模组 |

## 离线工具

| 目录 | 说明 |
|------|------|
| `tools/blueprint_lab/` | 离线蓝图分析和生成工具；用于解码蓝图字符串、扫描本地蓝图语料、提取紧凑布局经验，并生成第一版矩形黑盒种子蓝图 |

## 本地参考代码

`references/mods/` 可以存放第三方参考模组源码。这些目录只用于查阅和对照，不是本仓库自己的可打包模组，不参与 `pack_mods.py` 发现，也不会进入 Git。

## 目录约定

每个可打包模组都使用同一种源码布局：

```text
<mod>/
└── src/
    ├── info.json
    ├── control.lua
    ├── settings.lua
    ├── data.lua
    ├── data-updates.lua
    ├── data-final-fixes.lua
    └── locale/
```

并不是每个模组都需要所有入口文件。`pack_mods.py` 会从
`<mod>/src/info.json` 发现模组，并把 `src/` 内容打包到 Factorio 需要的
压缩包根目录中。

## 打包

在项目根目录运行：

```bash
python3 pack_mods.py
```

产物会写入 `ModZips/`，并在 Windows Factorio mods 目录存在时复制一份 zip 到该目录。文件名格式为：

```text
{info.name}_{info.version}.zip
```

压缩包内部的根目录也是：

```text
{info.name}_{info.version}/
```

在 WSL 中打包成功后，脚本会用 Windows 资源管理器打开 `ModZips/`。

## 调试部署

打包脚本会按模组自动处理 zip 复制和调试文件夹部署：

```text
%AppData%\Factorio\mods
```

注意事项：

- 成功打包后，脚本会把本轮生成的 `{info.name}_{info.version}.zip` 复制到该目录。
- 如果该目录已有 `{info.name}_*.zip`，脚本会跳过该模组的文件夹部署。
- 如果该目录没有 `{info.name}_*.zip`，脚本会复制本轮打包生成的 `{info.name}_{info.version}/` 文件夹。
- 不要直接把源码目录 `src/` 放进 Factorio mods 目录。

## 打包验证

```bash
python3 tests/verify_blueprint_lab.py
python3 tests/verify_pack_mods_ignores_non_runtime_files.py
python3 pack_mods.py
```

守卫测试会确认蓝图工具的编码/生成入口可用，并确认测试目录和仓库文档不会进入打包产物。打包命令输出
`Completed. Success: 6, Failed: 0` 时，表示当前 6 个模组都已成功生成 zip。

## Factorio 资料

- 官方 API 文档：`https://lua-api.factorio.com/latest/index.html`
- Data lifecycle：`https://lua-api.factorio.com/latest/auxiliary/data-lifecycle.html`
- Prototype 文档：`https://lua-api.factorio.com/latest/index-prototype.html`
- Runtime 文档：`https://lua-api.factorio.com/latest/index-runtime.html`
- Settings 教程：`https://wiki.factorio.com/Tutorial:Mod_settings`
- Modding tutorial：`https://wiki.factorio.com/Tutorial:Modding_tutorial/Gangsir`

实际行为以最新官方文档为准。
