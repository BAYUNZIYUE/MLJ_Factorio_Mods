# Section Autocraft

Scroll down for the Chinese version.

# What It Does

- Automatically hand-crafts missing items for the current player based on matching logistics sections.
- Uses a shortcut button to enable or disable autocrafting per player.
- Supports four section match modes: `Full match`, `Prefix`, `Player name`, and `Prefix + player name`.
- Can create a temporary missing-materials section when the selected craft target needs ingredients.
- Lets each player set their own hand crafting speed multiplier.
- Automatically decides how many crafts to queue from the current shortage and available materials.

The mod does not create any default logistics section by itself.

# When A Section Can Autocraft

A normal logistics section participates only when all conditions below are true.

| Condition | Required | If not satisfied |
| --- | --- | --- |
| Shortcut | Section Autocraft is enabled for the current player | Nothing is autocrafted |
| Section state | The logistics section itself is enabled | This section is ignored |
| Section type | The section is not the temporary missing-materials section | It is handled separately |
| Name match | The section name matches the current match mode | This section is ignored |
| Item shortage | The request still has a shortage after inventory, network, and queued crafts are counted | No craft is queued for that item |
| Recipe | The recipe is unlocked and currently craftable, or its missing ingredients can be requested | The item is skipped until materials or recipes are available |

# Examples

Assume the current player name is `PlayerName`.

`[wrench]` below means the wrench virtual signal prefix:
`[virtual-signal=signal-autocraft-wrench]`

| Match mode | Section name | Section enabled | Name matches | Autocrafts | Why |
| --- | --- | --- | --- | --- | --- |
| Full match | `Belts` | Yes | Yes | Yes | Full match accepts any enabled normal section |
| Full match | `Belts` | No | Yes | No | Disabled sections are ignored |
| Prefix | `Belts` | Yes | No | No | The name does not start with `[wrench]` |
| Prefix | `[wrench]Belts` | Yes | Yes | Yes | The name starts with the configured prefix |
| Player name | `PlayerName-Ore` | Yes | Yes | Yes | The name starts with the current player name |
| Player name | `OtherPlayer-Ore` | Yes | No | No | The name belongs to another player |
| Prefix + player name | `[wrench]PlayerName-Modules` | Yes | Yes | Yes | The name starts with both the prefix and current player name |
| Prefix + player name | `[wrench]OtherPlayer-Modules` | Yes | No | No | The prefix matches, but the player name does not |

# Shortage Calculation

For each requested item, Section Autocraft calculates:

```text
shortage = requested amount
         - items in the player's inventory
         - items already available in the current logistic network
         - items already queued for hand crafting
```

When crafting starts, the mod automatically chooses the craft count:

```text
craft count = min(
  crafts needed to cover the shortage,
  crafts currently possible with available materials,
  internal safety cap
)
```

This means it does not ask you to set a batch size, and it will not queue more than the logistics
request still needs.

# Settings

| Setting | Scope | Meaning |
| --- | --- | --- |
| Autocraft prefix | Per player | Rich text prefix used by `Prefix` and `Prefix + player name` modes |
| Autocraft match mode | Per player | Selects which section names are allowed to participate |
| Play autocraft completion sound | Per player | Plays a sound when a mod-owned craft finishes |
| Hand crafting speed multiplier | Per player | How many times vanilla hand crafting speed to use for your character |

# Acknowledgements

Special thanks to nmalaguti's Autocraft mod
([autocraft-logistics](https://mods.factorio.com/mod/autocraft-logistics)). This mod exists
because it was inspired by that work.

Special thanks to Meister177's Faster Hand Crafting Speed mod
([faster-hand-crafting-speed](https://mods.factorio.com/mod/faster-hand-crafting-speed)).
Section Autocraft's hand crafting speed setting is based on that mod's approach.

Special thanks to BAYUNZIYUE for discussing the implementation logic together and helping test the
mod.

# 模组功能

- 根据匹配到的物流编组，为当前玩家自动手搓缺少的物品。
- 使用右下角快捷按钮为每个玩家单独开启或关闭自动手搓。
- 支持四种编组匹配模式：`全匹配`、`前缀`、`玩家名`、`前缀 + 玩家名`。
- 当前手搓目标缺少原料时，可以创建临时“缺失材料编组”来请求原料。
- 每个玩家可以单独设置自己的手搓速度倍数。
- 自动根据当前缺口和可用材料决定本轮制作数量。

模组本身不会自动创建任何默认物流编组。

# 自动手搓什么时候生效

一个普通物流编组只有同时满足下面所有条件，才会参与自动手搓。

| 条件 | 必须满足 | 不满足时 |
| --- | --- | --- |
| 快捷开关 | 当前玩家已开启 Section Autocraft | 不自动手搓 |
| 编组状态 | 物流编组本身已启用 | 忽略这个编组 |
| 编组类型 | 不是临时“缺失材料编组” | 由缺料逻辑单独处理 |
| 名称匹配 | 编组名称符合当前匹配模式 | 忽略这个编组 |
| 物品缺口 | 扣除背包、物流网络、手搓队列后仍有缺口 | 不为这个物品排队 |
| 配方状态 | 配方已解锁且当前可制作，或可以请求缺少的原料 | 暂时跳过这个物品 |

# 实际例子

假设当前玩家名是 `PlayerName`。

下面表格里的 `[扳手]` 表示扳手虚拟信号前缀：
`[virtual-signal=signal-autocraft-wrench]`

| 匹配模式 | 编组名称 | 编组已启用 | 名称匹配 | 会自动手搓 | 原因 |
| --- | --- | --- | --- | --- | --- |
| 全匹配 | `Belts` | 是 | 是 | 是 | 全匹配接受所有已启用的普通编组 |
| 全匹配 | `Belts` | 否 | 是 | 否 | 已禁用的编组会被忽略 |
| 前缀 | `Belts` | 是 | 否 | 否 | 名称不是以 `[扳手]` 开头 |
| 前缀 | `[扳手]Belts` | 是 | 是 | 是 | 名称以配置的前缀开头 |
| 玩家名 | `PlayerName-Ore` | 是 | 是 | 是 | 名称以当前玩家名开头 |
| 玩家名 | `OtherPlayer-Ore` | 是 | 否 | 否 | 名称属于其他玩家 |
| 前缀 + 玩家名 | `[扳手]PlayerName-Modules` | 是 | 是 | 是 | 名称同时满足前缀和当前玩家名 |
| 前缀 + 玩家名 | `[扳手]OtherPlayer-Modules` | 是 | 否 | 否 | 前缀匹配，但玩家名不匹配 |

# 缺口计算方式

对每一种请求物品，Section Autocraft 会这样计算缺口：

```text
缺口 = 物流请求数量
     - 玩家背包里已有的数量
     - 当前物流网络里已有的数量
     - 已经排进手搓队列的数量
```

开始手搓时，模组会自动决定制作次数：

```text
制作次数 = min(
  覆盖当前缺口需要的制作次数,
  当前材料实际能制作的次数,
  内部安全上限
)
```

也就是说，你不需要手动设置批量数量；模组不会排入超过物流请求仍然需要的数量。

# 设置说明

| 设置 | 范围 | 作用 |
| --- | --- | --- |
| 自动手搓前缀 | 每玩家 | `前缀` 和 `前缀 + 玩家名` 模式使用的富文本前缀 |
| 自动手搓匹配模式 | 每玩家 | 选择哪些编组名称允许参与自动手搓 |
| 播放自动手搓完成音效 | 每玩家 | 模组排入的手搓完成时播放音效 |
| 手搓速度倍数 | 每玩家 | 当前玩家的手搓速度是原版速度的多少倍 |

# 致谢

特别感谢 nmalaguti 的 Autocraft 模组
([autocraft-logistics](https://mods.factorio.com/mod/autocraft-logistics))，正是受到这个模组的启发，
才有了现在这个模组。

特别感谢 Meister177 的 Faster Hand Crafting Speed 模组
([faster-hand-crafting-speed](https://mods.factorio.com/mod/faster-hand-crafting-speed))。
Section Autocraft 的手搓速度设置参考了这个模组的实现思路。

特别感谢 BAYUNZIYUE，与我一起讨论模组实现逻辑，并参与模组测试。
