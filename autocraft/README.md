# Autocraft

A [Factorio](https://factorio.com/) mod for automatically hand-crafting items based on matching
logistics sections. A wrench virtual signal can be used as a configurable prefix, and the match
mode can be switched between full match, prefix, player name, and prefix+player name. When the
shortcut is enabled, Autocraft automatically hand-crafts missing items for the current player.
It does not create any default logistics section automatically.

这是一个 [Factorio](https://factorio.com/) 自动手搓模组。它会根据匹配的物流编组
自动补做当前玩家缺少的物品。你可以把扳手虚拟信号作为可配置前缀，并在“全匹配 / 前缀 /
玩家名 / 前缀+玩家名”之间切换匹配模式。开启右下角快捷按钮后，Autocraft 会开始自动手搓。
模组不会自动创建任何默认物流编组。

Missing amount is calculated from the combined section requests, then reduced by:

- items already in the player's inventory
- items already present in the current logistic network
- items already queued for hand crafting

缺口数量会先按所有参与计算的物流编组合并，然后再扣除：

- 玩家背包里已经有的数量
- 当前物流网络里已经有的数量
- 当前已经排进手搓队列的数量

## Download / 下载

Download on the [Factorio mod portal](https://mods.factorio.com/mod/autocraft),
either on the website or in-game.

可在 [Factorio 模组门户](https://mods.factorio.com/mod/autocraft) 下载，
也可以直接在游戏内安装。

## Screenshots / 截图

TODO: take screenshots

# Development / 开发

Autocraft now lives directly as Lua source under `src/`.

Autocraft 现在直接以 Lua 源码形式维护在 `src/` 目录下。

```bash
# package all mods in this workspace
python3 pack_mods.py
```

```bash
# 打包当前工作区中的所有模组
python3 pack_mods.py
```

For hot-reload style debugging, extract the packaged mod folder (the archive root directory, not
`src/`) into `%AppData%\Factorio\mods` and remove any older zip or folder version of the same mod
before launching the game.

如果要用热重载式流程调试，请把打包后压缩包里的模组根目录文件夹
（也就是压缩包最外层那一层，不是 `src/`）解压到 `%AppData%\Factorio\mods`，
并在启动游戏前移除同模组的旧 zip 或旧文件夹版本。

### Autocraft prefix / 自动手搓前缀

The prefix is configured with the wrench virtual signal, sourced from
https://www.svgrepo.com/svg/286868/wrench-repair under a CC0 license.

前缀使用扳手虚拟信号配置，图标来源为
https://www.svgrepo.com/svg/286868/wrench-repair ，许可为 CC0。

### Match modes / 匹配模式

`Full match / 全匹配`: every section can autocraft.

`Prefix / 前缀`: sections whose names start with the configured prefix can autocraft.

`Player name / 玩家名`: sections whose names start with the current player name can autocraft.

`Prefix + player name / 前缀+玩家名`: sections whose names start with the configured prefix followed by the current player name can autocraft.

### Shortcut / 快捷按钮

The lower-right shortcut toggles autocrafting on and off. Turning it off cancels the module-owned crafting queue and clears active autocraft state. The default state is enabled.

右下角快捷按钮用于开启或关闭自动手搓。关闭时会取消模组建立的手搓队列，并清空当前自动手搓状态。默认状态为启用。

### Missing materials section / 缺失材料编组

When the current hand-craft target is missing ingredients, Autocraft can create a temporary logistics section that requests missing materials recursively. The section is created only when needed, forced to stay enabled while it exists, and deleted immediately once the player inventory has enough materials to continue crafting.

当当前手搓目标缺少原料时，Autocraft 会创建一个临时物流编组，用于递归请求缺失材料。该编组只在需要时创建，存在期间会被强制保持启用；当玩家背包材料已经足够继续手搓时，会立即删除。

# Icons / 图标

This project includes icons from Flaticon, which are licensed under their respective licenses.

本项目使用了来自 Flaticon 的图标资源，并遵循其各自的授权协议。

- <a href="https://www.flaticon.com/free-icons/busy" title="busy icons">Thumbnail icon created by noomtah - Flaticon</a>
- <a href="https://www.flaticon.com/free-icons/automation" title="automation icons">Shortcut icons created by Freepik - Flaticon</a>
