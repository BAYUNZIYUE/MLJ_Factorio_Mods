# Dynamic Inventory

Dynamic Inventory automatically adjusts the player's inventory bonus slots so
there is enough empty space while playing.

Scroll down for the Chinese version.

## What It Does

- Watches the player's main inventory.
- Expands the character inventory bonus when free slots are below the configured target.
- Avoids resizing while the player is interacting with another GUI unless free slots are already low.
- Rechecks delayed resize requests once per second.

## Settings

| Setting | Scope | Default | Meaning |
| --- | --- | --- | --- |
| Min inventory slots bonus | Per player | `0` | Minimum number of bonus inventory slots to keep |
| Empty inventory slots | Per player | `120` | Target number of empty slots to keep available |

## Notes

- The mod only changes the character inventory slot bonus.
- It does not add items, remove items, or change stack sizes.
- The resize logic only runs while the player has a character and a main inventory.

# 动态背包

Dynamic Inventory 会自动调整玩家背包奖励格子数，让游玩过程中保留足够的空槽位。

## 模组功能

- 监听玩家主背包变化。
- 当空槽数量低于配置目标时，自动扩展角色背包奖励格子数。
- 玩家正在打开其他界面时，不会频繁调整背包；只有空槽已经偏低时才会继续扩容。
- 延迟调整的玩家会每秒重新检查一次。

## 设置

| 设置 | 范围 | 默认值 | 作用 |
| --- | --- | --- | --- |
| 最小背包奖励格子数 | 每玩家 | `0` | 背包额外扩容的最低数量 |
| 背包空槽数 | 每玩家 | `120` | 希望持续保留的空槽数量 |

## 说明

- 模组只调整角色背包奖励格子数。
- 模组不会添加物品、删除物品或修改堆叠大小。
- 调整逻辑只在玩家拥有角色和主背包时生效。
