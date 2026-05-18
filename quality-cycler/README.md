> 下拉以查看中文说明。

# Blueprint & Upgrade Planner Quality Cycler

## Overview

Blueprint & Upgrade Planner Quality Cycler lets you raise or lower qualities inside blueprints, blueprint books, and upgrade planners with the controls bound to quality up/down.

## Features

- Changes the quality of blueprint entities with functional quality effects, including cargo bays, thrusters, turrets, and other combat buildings.
- Changes the quality of modules and other requested items stored inside blueprint entities.
- Recursively processes blueprint books and prints one combined result.
- Changes only the target quality in upgrade planners, so broad rules such as `any quality -> legendary` keep their source side unchanged.
- Reads the active quality chain from the game, so expanded quality mods are supported without hard-coded quality names.
- Skips transport belts, underground belts, and splitters by default.
- Adds a per-player ignore list setting for prototype names that should not be changed.

## Usage

### Basic workflow

- Put a blueprint, blueprint book, or upgrade planner in your inventory, or move it to Public blueprints.
- Hold the item on the cursor or select a writable Public blueprint or upgrade-planner record.
- Use the controls bound to quality up/down; quality up raises eligible targets by one step, and quality down lowers eligible targets by one step.
- Records in My blueprints are read-only to mods, so move them to inventory or Public blueprints before using this mod.
- Opening a blueprint or upgrade-planner window and hovering a single row does not expose enough writable row information to mods, so this mod edits the writable item or record as a whole.

### What gets changed

- Eligible blueprint entities include machines and buildings with functional quality effects, such as cargo bays, thrusters, turrets, logistic chests, roboports, pumps, heating towers, labs, asteroid collectors, and fusion power buildings.
- Stored blueprint items such as modules are changed when their item prototype or placed result has a quality effect.
- Transport belts, underground belts, and splitters are skipped by default because their quality is usually not a functional upgrade target in blueprints.
- If another mod adds quality-specific tooltip values to an entity or item, this mod treats that as a quality effect and may update it unless it is skipped or ignored.

### Upgrade planners

- Upgrade planners are edited on the target side only.
- A rule like `any quality -> rare` becomes `any quality -> epic` when quality up is used.
- The source side stays unchanged, so wide matching rules continue to match the same source set.
- Lowering quality can move `rare` back to no stored quality when the target is one step above normal.

### Ignore list

- The setting `Quality cycling ignore list` is runtime-per-user, so every player can keep a different list.
- Enter prototype names separated by commas, for example `transport-belt,fast-inserter`.
- Chinese commas are also accepted.
- Ignored names are matched exactly against the blueprint entity, stored item, or upgrade-planner target name.

### Examples

- If a blueprint contains cargo bays, thrusters, laser turrets, gun turrets, logistic chests, and stored module requests, quality up raises those eligible targets by one quality step.
- If the same blueprint also contains transport belts, underground belts, and splitters, those belt-family entities stay unchanged.
- If an upgrade planner contains `any quality -> rare`, quality up changes only the target side to the next quality and keeps the source side broad.
- If you put `fast-inserter` in the ignore list, fast inserters are left unchanged even when other eligible inserters in the same blueprint are changed.

## Acknowledgments

- Thanks to every player who uses this mod.

If you have any comments or suggestions, please share them in the [Factorio discussion](http://mods.factorio.com/mod/quality-cycler/discussion) or on [GitHub](https://github.com/MengLeiFudge/MLJ_Factorio_Mods/tree/master/quality-cycler).

# 中文说明

## 概览

蓝图/绿图品质切换器可以使用控制设置里绑定的品质上/下切换操作，提高或降低蓝图、蓝图册和绿图中的品质。

## 功能简介

- 修改蓝图中有功能性品质效果的建筑品质，包括货仓、飞船推进器、炮塔和其他战斗建筑。
- 修改蓝图建筑内部保存的插件、模块等物品品质。
- 递归处理蓝图册，并在完成后输出一条汇总结果。
- 只修改绿图的目标品质，不修改来源品质，因此 `任意品质 -> 传说品质` 这类规则仍会保持来源侧的宽泛匹配。
- 从游戏当前启用的品质链动态读取品质顺序，兼容扩展品质模组。
- 默认跳过传送带、地下传送带和分流器。
- 新增每玩家屏蔽列表设置，可填写更多不希望被修改的原型名。

## 使用说明

### 基本流程

- 将蓝图、蓝图册或绿图放在背包中，或移动到公共蓝图。
- 手持该物品，或选中可写的公共蓝图/绿图记录。
- 使用控制设置里绑定的品质上/下切换操作；品质上会让可修改目标升一档，品质下会让可修改目标降一档。
- “我的蓝图”中的记录对模组只读，需要先移动到背包或公共蓝图再使用。
- 打开蓝图或绿图窗口并悬停单行时，游戏不会向模组暴露足够的可写行信息，因此本模组会整体修改当前可写物品或记录。

### 哪些对象会被修改

- 可修改的蓝图建筑包括有功能性品质效果的机器和建筑，例如货仓、飞船推进器、炮塔、物流箱、机器人指令平台、抽水泵、供热塔、研究中心、星岩抓取器和聚变发电建筑。
- 蓝图建筑里保存的插件等物品，如果该物品本身或它放置后的结果有品质效果，也会一起修改。
- 传送带、地下传送带和分流器默认跳过，因为它们在蓝图里通常不是玩家想批量调整品质的功能性目标。
- 如果其他模组给某个实体或物品添加了按品质变化的提示字段，本模组会把它视为有品质效果；除非它被默认跳过或写入屏蔽列表。

### 绿图

- 绿图只修改目标侧品质。
- 例如 `任意品质 -> 稀有品质` 在使用品质上后会变成 `任意品质 -> 史诗品质`。
- 来源侧保持不变，因此宽泛匹配规则仍然匹配同一批来源对象。
- 使用品质下时，目标品质可以从稀有降回无品质。

### 屏蔽列表

- `品质切换屏蔽列表` 是每玩家运行时设置，因此每个玩家可以维护自己的列表。
- 填写不希望被修改的原型名，用逗号隔开，例如 `transport-belt,fast-inserter`。
- 中文逗号也可以使用。
- 屏蔽列表会精确匹配蓝图实体、建筑内保存的物品或绿图目标的原型名。

### 例子

- 如果蓝图里有货仓、飞船推进器、激光炮塔、机枪炮塔、物流箱和保存的插件请求，品质上会把这些符合条件的目标一起升一档。
- 如果同一张蓝图里还有传送带、地下传送带和分流器，这些传送带类实体会保持不变。
- 如果绿图里有 `任意品质 -> 稀有品质`，品质上只会修改目标侧品质，来源侧仍保持任意品质。
- 如果在屏蔽列表里填写 `fast-inserter`，那么即使同一张蓝图里的其他机械臂会被修改，快速机械臂也会保持不变。

## 致谢

- 感谢所有使用此模组的玩家。

如果有任何意见或建议，欢迎在 [Factorio 讨论区](http://mods.factorio.com/mod/quality-cycler/discussion) 或 [GitHub](https://github.com/MengLeiFudge/MLJ_Factorio_Mods/tree/master/quality-cycler) 反馈。
