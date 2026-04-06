# Section Autocraft

Scroll down for the Chinese version.

# Mod Introduction

Section Autocraft is a Factorio mod that automatically hand-crafts missing items for the current player
based on matching logistics sections. It supports a configurable wrench virtual signal prefix and
multiple section matching modes. The mod does not create any default logistics section by itself.

# Mod Guide

## How the mod works

Section Autocraft combines the requests from the logistics sections that match the current configuration,
then subtracts:

- items already in the player's inventory
- items already available in the current logistic network
- items already queued for hand crafting

If the current hand-craft target is missing ingredients, the mod can create a temporary logistics
section for those missing materials. Once the player has enough materials to continue crafting,
that temporary section is removed automatically.

## How to use it

1. Decide which logistics sections Section Autocraft is allowed to read by choosing a match mode.
2. If you use `Prefix` or `Prefix + player name`, set the wrench virtual signal text as your
   naming prefix first. The default mode is `Prefix + player name`.
3. Enable the lower-right shortcut to let Section Autocraft keep hand-crafting missing items from the
   sections that match your current rules.
4. Disable the shortcut when you want Section Autocraft to stop. Turning it off cancels the mod-owned
   crafting queue and clears the active autocraft state.
5. A logistics section is considered active for Section Autocraft only when all of the following
   are true: Section Autocraft is enabled, the section itself is enabled, and its name matches the current match
   mode. The temporary missing-materials section is handled separately and is not treated as a
   normal source section.

### Match modes

- `Full match`: every enabled logistics section participates in Section Autocraft. Use this when your
  character logistics are already dedicated to hand-crafting support and you do not need to split
  sections by purpose.
- `Prefix`: only enabled logistics sections whose names start with the configured prefix
  participate. Use this when you want to mark a shared set of Section Autocraft sections with one common
  tag.
- `Player name`: only enabled logistics sections whose names start with the current player name
  participate. Use this when multiple players share a save and each player keeps their own
  personal sections.
- `Prefix + player name`: only enabled logistics sections whose names start with the configured
  prefix followed by the current player name participate. Use this when you want both a shared
  Section Autocraft tag and per-player separation. This is the default mode.

Example names:

- `Prefix`: `[virtual-signal=signal-autocraft-wrench]Belts`
- `Player name`: `YourName-Rockets`
- `Prefix + player name`: `[virtual-signal=signal-autocraft-wrench]YourName-Modules`

# Acknowledgements

Special thanks to nmalaguti's Autocraft mod
([autocraft-logistics](https://mods.factorio.com/mod/autocraft-logistics)). This mod exists
because it was inspired by that work.

Special thanks to BAYUNZIYUE for discussing the implementation logic together and helping test the
mod.

# 模组简介

Section Autocraft 是一个 Factorio 自动手搓模组。它会根据匹配到的物流编组，自动为当前玩家补做缺少
的物品。模组支持用扳手虚拟信号作为可配置前缀，并提供多种编组匹配模式。模组本身不会自动创建
任何默认物流编组。

# 模组说明

## 模组逻辑

Section Autocraft 会先汇总当前配置下所有匹配物流编组的需求，然后再扣除：

- 玩家背包里已经有的数量
- 当前物流网络里已经有的数量
- 当前已经排进手搓队列的数量

如果当前手搓目标缺少原料，模组会临时创建一个“缺失材料编组”来请求这些原料；当玩家背包中的
材料已经足够继续手搓时，这个临时编组会自动删除。

## 如何使用

1. 先选择匹配模式，决定 Section Autocraft 允许读取哪些物流编组。
2. 如果你使用“前缀”或“前缀 + 玩家名”，记得先把扳手虚拟信号文本配置成你的命名前缀。
   模组默认模式是“前缀 + 玩家名”。
3. 点击右下角快捷按钮后，Section Autocraft 会持续补做当前规则下匹配到的缺失物品。
4. 再次关闭快捷按钮时，模组会停止自动手搓，同时取消模组建立的手搓队列并清空当前自动手搓状态。
5. 一个物流编组要真正参与自动手搓，必须同时满足：Section Autocraft 总开关已开启、该编组本身处于启用状态、
   编组名称符合当前匹配模式。临时生成的“缺失材料编组”会单独处理，不会当作普通来源编组参与统计。

### 匹配模式说明

- `全匹配`：所有已启用的物流编组都会参与自动手搓。适合你的角色物流本来就主要用于手搓补料，
  不需要再按用途拆分编组的情况。
- `前缀`：只有名字以已配置前缀开头的已启用物流编组会参与自动手搓。适合你想用一个统一标签
  标记“这批编组就是给 Section Autocraft 用”的情况。
- `玩家名`：只有名字以当前玩家名开头的已启用物流编组会参与自动手搓。适合多人联机时，每个
  玩家维护自己的专属物流编组。
- `前缀 + 玩家名`：只有名字以“已配置前缀 + 当前玩家名”开头的已启用物流编组会参与自动手搓。
  适合既想保留统一的 Section Autocraft 标记，又想把不同玩家的编组分开管理的情况。这也是默认模式。

命名示例：

- `前缀`：`[virtual-signal=signal-autocraft-wrench]Belts`
- `玩家名`：`YourName-Rockets`
- `前缀 + 玩家名`：`[virtual-signal=signal-autocraft-wrench]YourName-Modules`

# 致谢

特别感谢 nmalaguti 的 Autocraft 模组
([autocraft-logistics](https://mods.factorio.com/mod/autocraft-logistics))，正是受到这个模组的启发，
才有了现在这个模组。

特别感谢 BAYUNZIYUE，与我一起讨论模组实现逻辑，并参与模组测试。
