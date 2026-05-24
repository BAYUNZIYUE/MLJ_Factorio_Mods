> 下拉以查看中文说明。

# Expend Toolbar

## Overview

Expend Toolbar adds custom movable toolbars when the vanilla quickbar is not enough. You can place item slots, tool shortcuts, and inventory-aware buttons anywhere on the screen, then keep them visible while building, crafting, or using remote view.

## Features

- Create multiple draggable toolbars with sections and item slots.
- Add items from the cursor or item selector and use the slot as a quick pickup button.
- Show item counts from the current view inventory directly on item slots.
- Show tooltip tables for available item qualities across player, vehicle, remote logistic network, or space platform inventories.
- Supports quality up/down controls on toolbar items.
- Supports crafting from toolbar slots when the crafting option is enabled.
- Supports remote view, planet logistic networks, space platform hub inventories, vehicles, character trash, editor inventory, god inventory, and spidertron remotes.
- Toolbars can be collapsed, locked, aligned, hidden, or shown with shortcuts.

## Usage

### Create and arrange a toolbar

- Use the shortcut button or bind the `Create a toolbar` custom input.
- Drag the toolbar header to place it on the screen.
- Add sections and put item slots into the section table.
- Lock a toolbar when you do not want accidental layout changes.

### Use item slots

- Left-click a slot to pick that item from the current available inventory.
- Use the pipette control over a slot to pick the slot item as a ghost if it is not currently available.
- Hover a slot to see per-inventory counts and quality rows.
- Use quality up/down while hovering a slot to change the slot quality.
- If crafting is enabled, use the configured crafting controls over a slot to start hand crafting.

### Inventory counts and logistic networks

- In normal character view, the number shown on a slot is the count available from the player-facing main inventory group, including the character inventory, cursor stack, character trash, and enabled vehicle inventories.
- Personal-view logistic networks are shown in the tooltip as side inventory data. They help you judge nearby supply, but they do not inflate the slot's direct count overlay.
- In remote planet view, logistic network contents are the main visible inventory for slot counts.
- On a space platform, the hub main and trash inventories are counted for remote-view slots.

### Examples

- Put belts, inserters, power poles, and modules into a toolbar next to your build area. The slot number updates from your current inventory, so you can see when you are running out without opening the inventory window.
- Hover a rare assembler slot while standing near a logistic network. The tooltip can show your carried stock separately from nearby network stock, so you can decide whether to request or pick up more items.
- Switch to remote view on another planet and use the same toolbar to inspect whether the visible logistic network can supply the selected item.

## Acknowledgments

- Thanks to the original Toolbars mod design and implementation that this local mod is based on.
- Thanks to every player who uses this mod.

If you have any comments or suggestions, please share them in the [Factorio discussion](http://mods.factorio.com/mod/expend-toolbar/discussion) or on [GitHub](https://github.com/MengLeiFudge/MLJ_Factorio_Mods/tree/master/expend-toolbar).

# 中文说明

## 概览

Expend Toolbar 在原版快捷栏不够用时，提供可以自由移动的自定义工具栏。你可以把物品、工具和带库存数量提示的按钮放到屏幕任意位置，并在建造、手搓或远程视图中保持可见。

## 功能简介

- 创建多个可拖动工具栏，每个工具栏可以包含多个分区和物品槽。
- 从光标或物品选择器添加物品，并把槽位当作快速拿取按钮使用。
- 在物品槽上直接显示当前视图库存中的物品数量。
- 悬停物品槽时显示玩家、载具、远程物流网络或太空平台库存中的品质数量表。
- 支持对工具栏物品使用品质上/下切换控制。
- 开启手搓功能后，可以通过工具栏槽位触发手搓。
- 支持远程视图、星球物流网络、太空平台枢纽库存、载具、角色垃圾栏、编辑器库存、上帝模式库存和蜘蛛机甲遥控器。
- 工具栏可以折叠、锁定、对齐、隐藏或通过快捷键显示。

## 使用说明

### 创建和整理工具栏

- 使用快捷栏按钮，或给 `Create a toolbar` 自定义输入绑定按键。
- 拖动工具栏标题栏，把它放到屏幕上的合适位置。
- 添加分区，并把物品槽放入分区表格中。
- 不想误改布局时，可以锁定工具栏。

### 使用物品槽

- 左键点击物品槽，会从当前可用库存中拿取该物品。
- 在物品槽上使用吸管控制，如果当前没有可拿取物品，也可以拿起对应幽灵。
- 悬停物品槽，可以查看按库存和品质拆分的数量表。
- 悬停物品槽时使用品质上/下控制，可以改变该槽位保存的品质。
- 如果启用了手搓功能，可以在槽位上使用已配置的手搓控制开始手搓。

### 库存数量和物流网络

- 在普通角色视图中，物品槽上的数字来自玩家当前主要库存组，包括角色背包、光标物品、角色垃圾栏，以及启用后的载具库存。
- 普通角色视图里的物流网络会显示在悬停提示的侧边库存数据中，用来判断附近供应，但不会把物流网络数量加到槽位数字上。
- 在星球远程视图中，物流网络内容是槽位数字使用的主要库存。
- 在太空平台上，平台枢纽主库存和垃圾库存会计入远程视图槽位数字。

### 例子

- 把传送带、机械臂、电线杆和插件放到建造区旁边的工具栏里。槽位数字会随当前库存刷新，不打开背包也能看到哪些材料快用完。
- 悬停一个稀有组装机槽位时，如果你站在物流网络附近，提示表可以把身上数量和附近网络数量分开显示，方便判断是否需要补货。
- 切到另一个星球的远程视图后，可以继续使用同一个工具栏查看当前可见物流网络是否有指定物品。

## 致谢

- 感谢本地模组所基于的原 Toolbars 模组设计和实现。
- 感谢所有使用此模组的玩家。

如果有任何意见或建议，欢迎在 [Factorio 讨论区](http://mods.factorio.com/mod/expend-toolbar/discussion) 或 [GitHub](https://github.com/MengLeiFudge/MLJ_Factorio_Mods/tree/master/expend-toolbar) 反馈。
