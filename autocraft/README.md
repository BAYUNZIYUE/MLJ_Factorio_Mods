# Autocraft

A [Factorio](https://factorio.com/) mod for automatically hand-crafting items based on
a logistics section named `Autocraft-<player name>`. When that section is active, Autocraft
automatically hand-crafts missing items for the current player. It can also include other active
logistics sections when the `Existing sections use autocraft` runtime-per-user setting is enabled.

这是一个 [Factorio](https://factorio.com/) 自动手搓模组。它会根据名为 `Autocraft-<玩家名>`
的物流编组，为当前玩家自动补做缺少的物品。当该编组处于激活状态时，Autocraft 会参与自动手搓。
如果启用了 `Existing sections use autocraft` 这个玩家运行时设置，还会把其他已激活的普通物流编组
一并纳入自动手搓计算。

Missing amount is calculated from the combined section requests, then reduced by:

- items already in the player's inventory
- items already present in the current logistic network
- items already queued for hand crafting

缺口数量会先按所有参与计算的物流编组合并，然后再扣除：

- 玩家背包里已经有的数量
- 当前物流网络里已经有的数量
- 当前已经排进手搓队列的数量

## Download

Download on the [Factorio mod portal](https://mods.factorio.com/mod/autocraft),
either on the website or in-game.

可在 [Factorio 模组门户](https://mods.factorio.com/mod/autocraft) 下载，
也可以直接在游戏内安装。

## Screenshots

TODO: take screenshots

# Development

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

# Icons

This project includes icons from Flaticon, which are licensed under their respective licenses.

本项目使用了来自 Flaticon 的图标资源，并遵循其各自的授权协议。

- <a href="https://www.flaticon.com/free-icons/busy" title="busy icons">Thumbnail icon created by noomtah - Flaticon</a>
- <a href="https://www.flaticon.com/free-icons/automation" title="automation icons">Shortcut icons created by Freepik - Flaticon</a>
