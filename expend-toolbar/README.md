> 下拉以查看中文说明。

# Expend Toolbar

## Overview

Expend Toolbar adds custom movable toolbars when the vanilla quickbar is not enough. You can place item slots, tool shortcuts, and inventory-aware buttons anywhere on the screen, then keep them visible while building or using remote view.

## Features

- Keep one default draggable custom bar with ten fixed numbered pages and item slots.
- Switch pages with the bottom 1-10 page buttons; only the active page is shown.
- Rename toolbar pages by double-clicking a page button.
- Add items with the slot item selector and use saved slots as quick pickup buttons.
- Copy and paste the hovered row or the hovered numbered page with optional custom controls.
- Show item counts from the current view inventory directly on item slots.
- Show saved item quality markers on item slots.
- Show tooltip tables for available item qualities across player, vehicle, remote logistic network, or space platform inventories.
- Supports quality up/down controls on toolbar items.
- Supports remote view, planet logistic networks, space platform hub inventories, vehicles, character trash, editor inventory, and god inventory.
- Custom bars can be moved by their drag anchor and hidden or shown with the toolbar shortcut.

## Usage

### Arrange the toolbar

- The toolbar is created automatically for each player and starts near the bottom center of the screen.
- Use the toolbar shortcut to show or hide the toolbar; the shortcut toggle matches the current visibility.
- Drag the striped anchor in the toolbar header to place it on the screen.
- Put item slots into any of the ten numbered pages.

### Configure numbered pages

- Set `Toolbar columns` in per-user mod settings. The default is 10 columns.
- Each numbered page keeps that horizontal slot count.
- The toolbar height follows the currently active page.
- Rows expand automatically when the last slot of the last row is occupied.
- Empty trailing rows shrink automatically when the previous row does not need the extra row.
- The bottom page buttons share the toolbar width; narrow buttons show page numbers, while wider buttons show page titles.
- Double-click a page button to rename that page.

### Use item slots

- Left-click a slot to pick that item from the current available inventory.
- Left-click another toolbar slot after selecting a slot to move the saved entry there; the source slot is cleared.
- Middle-click or right-click a slot to clear it.
- Hover a slot to see per-inventory counts and quality rows.
- Use quality up/down while hovering a slot to change the slot quality.
- Use the Factoriopedia control while hovering a slot to inspect the item.
- Bind `Copy toolbar row or page` and `Paste toolbar row or page` in controls if you want row/page duplication. Hover a slot row to copy or paste that row; hover a page number to copy or paste the whole page.

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

- Thanks to the Factorio modding documentation and community examples that helped shape this rewrite.
- Thanks to every player who uses this mod.

If you have any comments or suggestions, please share them in the [Factorio discussion](http://mods.factorio.com/mod/expend-toolbar/discussion) or on [GitHub](https://github.com/MengLeiFudge/MLJ_Factorio_Mods/tree/master/expend-toolbar).

# 中文说明

## 概览

Expend Toolbar 在原版快捷栏不够用时，提供可以自由移动的自定义工具栏。你可以把物品、工具和带库存数量提示的按钮放到屏幕任意位置，并在建造或远程视图中保持可见。

## 功能简介

- 每名玩家默认拥有一个可拖动自定义栏，每个自定义栏固定包含 10 个数字页面和物品槽。
- 使用底部 1-10 页面按钮切换页面；同一时间只显示当前激活页面。
- 双击页面按钮可以重命名工具栏页面。
- 通过槽位物品选择器添加物品，并把保存的槽位当作快速拿取按钮使用。
- 可以通过可选快捷键复制和粘贴当前悬停的行或数字页面。
- 在物品槽上直接显示当前视图库存中的物品数量。
- 在物品槽上显示已保存物品品质的角标。
- 悬停物品槽时显示玩家、载具、远程物流网络或太空平台库存中的品质数量表。
- 支持对工具栏物品使用品质上/下切换控制。
- 支持远程视图、星球物流网络、太空平台枢纽库存、载具、角色垃圾栏、编辑器库存和上帝模式库存。
- 自定义栏可以通过拖动锚点移动，并可以通过快捷键隐藏或显示。

## 使用说明

### 整理工具栏

- 工具栏会为每名玩家自动创建，并默认出现在屏幕底部中间。
- 使用工具栏快捷按钮隐藏或显示工具栏；快捷按钮开关状态会匹配当前显示状态。
- 拖动工具栏标题栏中的条纹锚点，把它放到屏幕上的合适位置。
- 把物品槽放入 10 个数字页面中的任意页面。

### 配置数字页面

- 在个人模组设置里设置 `工具栏列数`。默认值是 10 列。
- 每个数字页面都会保持这个横向槽位数。
- 工具栏高度会跟随当前激活页面。
- 当最后一行最后一个槽位被占用时，会自动新增一行。
- 当末尾空行不再需要时，会自动连续收缩多余行。
- 底部分页按钮会平分工具栏宽度；按钮较窄时显示页码，较宽时显示页面标题。
- 双击分页按钮可以重命名页面。

### 使用物品槽

- 左键点击物品槽，会从当前可用库存中拿取该物品。
- 选中一个槽位后再左键点击另一个工具栏槽位，会把保存项移动过去，并清空来源槽位。
- 中键或右键点击物品槽可以清空槽位。
- 悬停物品槽，可以查看按库存和品质拆分的数量表。
- 悬停物品槽时使用品质上/下控制，可以改变该槽位保存的品质。
- 悬停物品槽时使用 Factoriopedia 控制，可以查看物品百科。
- 如果需要复制页面或整行，可以在控制设置中绑定 `Copy toolbar row or page` 和 `Paste toolbar row or page`。悬停某一行的槽位时复制或粘贴该行；悬停页面数字时复制或粘贴整页。

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

- 感谢 Factorio 模组文档和社区示例为这次重写提供参考。
- 感谢所有使用此模组的玩家。

如果有任何意见或建议，欢迎在 [Factorio 讨论区](http://mods.factorio.com/mod/expend-toolbar/discussion) 或 [GitHub](https://github.com/MengLeiFudge/MLJ_Factorio_Mods/tree/master/expend-toolbar) 反馈。
