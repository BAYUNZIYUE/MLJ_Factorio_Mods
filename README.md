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

产物会写入 `ModZips/`，文件名格式为：

```text
{info.name}_{info.version}.zip
```

压缩包内部的根目录也是：

```text
{info.name}_{info.version}/
```

在 WSL 中打包成功后，脚本会用 Windows 资源管理器打开 `ModZips/`。

## 调试部署

调试某个模组时，优先把解压后的模组文件夹放到：

```text
%AppData%\Factorio\mods
```

注意事项：

- 放入的是压缩包内部那层 `{info.name}_{info.version}/` 文件夹。
- 不要直接把源码目录 `src/` 放进 Factorio mods 目录。
- 部署新版本前，先移除同一模组的旧 `.zip` 或旧文件夹。
- 不要让同一模组的旧版本 zip 和新版本文件夹同时存在。

## 打包验证

```bash
python3 tests/verify_pack_mods_ignores_non_runtime_files.py
python3 pack_mods.py
```

守卫测试会确认测试目录和仓库文档不会进入打包产物。打包命令输出
`Completed. Success: 6, Failed: 0` 时，表示当前 6 个模组都已成功生成 zip。

## Factorio 资料

- 官方 API 文档：`https://lua-api.factorio.com/latest/index.html`
- Data lifecycle：`https://lua-api.factorio.com/latest/auxiliary/data-lifecycle.html`
- Prototype 文档：`https://lua-api.factorio.com/latest/index-prototype.html`
- Runtime 文档：`https://lua-api.factorio.com/latest/index-runtime.html`
- Settings 教程：`https://wiki.factorio.com/Tutorial:Mod_settings`
- Modding tutorial：`https://wiki.factorio.com/Tutorial:Modding_tutorial/Gangsir`

实际行为以最新官方文档为准。
