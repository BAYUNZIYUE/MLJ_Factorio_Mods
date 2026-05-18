> 下拉以查看中文说明。

# Dynamic Inventory

## Overview

Dynamic Inventory automatically adjusts inventory size so the player keeps enough empty space while playing.

## Features

- Automatically increases the character inventory slot bonus when the main inventory has fewer empty slots than the configured target.
- Keeps a configurable minimum inventory bonus, so the inventory never shrinks below the player-selected baseline.
- Delays non-urgent resizing while the player is interacting with another GUI, reducing disruptive inventory changes during normal play.
- Rechecks delayed resize requests once per second until the player can be resized safely.

## Usage

- Configure `Min inventory slots bonus` to set the minimum number of bonus inventory slots your character should keep.
- Configure `Empty inventory slots` to set how many empty inventory slots the mod should try to keep available.
- The resize logic works only while the player has a valid character and main inventory.
- The mod only changes the character inventory slot bonus; it does not add items, remove items, or change stack sizes.

### Example

If `Empty inventory slots` is set to `120` and your inventory drops below that target, the mod increases your character inventory bonus until there is enough free space again.

## Acknowledgments

- Thanks to every player who uses this mod.

If you have any comments or suggestions, please share them in the [Factorio discussion](http://mods.factorio.com/mod/DynamicInventory/discussion) or on [GitHub](https://github.com/MengLeiFudge/MLJ_Factorio_Mods/tree/master/DynamicInventory).

# 中文说明

## 概览

动态背包会自动调整背包大小，以确保玩家在游玩过程中保留足够的空槽位。

## 功能简介

- 当主背包空槽数低于设置目标时，自动提高角色背包奖励格子数。
- 保留可配置的最低背包奖励格子数，避免背包低于玩家设置的基础容量。
- 玩家正在操作其他界面且空槽尚未过低时，会延后非紧急扩容，减少游玩过程中的突兀变化。
- 已延后的扩容请求会每秒重新检查一次，直到可以安全调整。

## 使用说明

- 设置 `最小背包奖励格子数`，决定角色至少保留多少额外背包格。
- 设置 `背包空槽数`，决定模组尽量维持多少空背包格。
- 调整逻辑只在玩家拥有有效角色和主背包时生效。
- 模组只修改角色背包奖励格子数，不会添加物品、删除物品或修改堆叠大小。

### 例子

如果 `背包空槽数` 设置为 `120`，而你的背包空槽低于这个目标，模组就会提高角色背包奖励格子数，直到重新拥有足够空位。

## 致谢

- 感谢所有使用此模组的玩家。

如果有任何意见或建议，欢迎在 [Factorio 讨论区](http://mods.factorio.com/mod/DynamicInventory/discussion) 或 [GitHub](https://github.com/MengLeiFudge/MLJ_Factorio_Mods/tree/master/DynamicInventory) 反馈。
