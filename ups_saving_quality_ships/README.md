> "Get rid of computer performance and enjoy the ultimate technology!" —— Promethium Tech Pack Spaceship
>
> “摆脱电脑性能，畅享终极科技！” —— 黑瓶飞船

翻到下面以查看中文介绍

# Mod introduction

## Mod effect

* The p-value (i.e. the multiplier used by this mod to approximate multiple identical ships) is determined by the
  quality of the ship's center hub.
* Ground => Space: the mod scales the ship's request to roughly px cargo, then reduces the contents after the cargo
  pods arrive so that the visible ship finally keeps about x cargo.
* Space => Ground: the mod tries to create extra cargo pods so the ground can receive up to about px cargo while the
  ship only consumes x cargo. If extra pods cannot be created, the remaining cargo is returned to the hub/cache.

## What does it do?

This mod is designed to optimize game lag issues caused by multiple ships of the same function running at the same
time (common in late game when making engineering bases and promethium tech packs). If each of your ships is a different
function, then it probably won't affect you much; if you like copying and pasting ships together, then it's perfect for
you!

Assuming that capacity and capacity remain the same, if a single ship can serve the function of several previous ships,
then you can reduce the number of ships, which in turn will have the effect of improving the ups. This is especially
true of ships that make promethium tech packs, which generate a lot of astroliths as they fly around the shattered edge,
resulting in a sharp drop in ups. Even if you only have one of these ships, with this mod your xenomorph egg
consumption, quantum processor consumption, and black vial output will all be p times what they were before, and less
time spent running on the Broken Edge will also mean higher ups. so this mod is suitable for any late-stage archive -
even if you don't have a ship with the same functionality.

## Is it part of a cheat mod?

One might ask if it is possible to reduce the number of star rocks and add multiples of them to the grapple arm after
capture, if only to solve the lag caused by too many star rocks? I've thought about this, but I think it would be easy
to implement, but not as “balanced”. For example, if the number of star rocks decreases, should the blood level of the
star rocks also be multiplied? If the ship uses a lot of blaster rockets with the increased blood, should the damage of
the blaster rockets be doubled? I think its hard to achieve the same experience as the original.

Instead, the mod uses a UPS-oriented approximation of “several identical ships hidden behind one visible ship”. It only
changes cargo interaction and does not try to perfectly reproduce every physical limit of several real ships (for
example, it does not add extra cargo hatches by itself). In other words, it is designed to preserve the overall cargo
result better than a simple resource multiplier, but it is still an approximation rather than a strict one-to-one
simulation. The only cheat is that it pretends to increase your computer's configuration :)

## How it works

## How the multiplier is calculated

The simulation multiplier p is related to the quality of the platform's hub (and arguably the quality of the platform's
starter pack).

| Hub quality | Quality level | Simulation multiplier | 
|:-----------:|:-------------:|:---------------------:| 
|   normal    |       0       |           1           | 
|  uncommon   |       1       |           2           | 
|    rare     |       2       |           3           | 
|    epic     |       3       |           4           | 
|  legendary  |       5       |           5           |

The reason why the analog multiplier for the Legendary Space Platform Hub isn't 6x is because I found 6x to be too hard
to use and a pain in the ass when calculating requirements.

If you're interested, the actual formula used is:

`p = 1 + math.celi(Space Platform Hub quality level x 0.79)`

This way, it's also compatible with some extended quality mods.

## Ground => Space

Cargo will go through the following steps to get from ground to space:

1. the ship requests x cargo from the ground (In practice, the mod automatically generates a dynamic logistics group.)
2. the dynamic logistics group makes the ground side try to send about px cargoes in total.
3. after each cargo pod arrives on the platform surface, the mod checks its inventory and removes about (p-1)/p of the
   contents (**rounded through the cache logic described below**).
4. the visible ship finally keeps about x cargo.

This means the mod matches the overall throughput by changing requests and post-arrival pod contents. It does **not**
increase the number of cargo hatches or try to claim that one visible ship now has the exact same receiving interface
count as p separate ships.

You will no doubt notice that the processing in step 3 is the trickiest, especially in the following cases:

* What about individual rockets with cargoes that are not a multiple of p?
* What about cargoes with very small rocket loads (e.g. a rocket load of 1)?

Don't worry, this mod provides an invisible cache for such cases.

In simple terms, the excess deduction is added to the cache and will be reused the next time the same item/quality is
transported.

For example if a single rocket load is 100 and p=3, then:

* the first rocket deducts 67 cargo, 1 cargo is added to the cache, and the ship receives 33 cargoes
* The second rocket deducts 67 cargo, 1 cargo is added to the cache, and the ship receives 33 cargoes.
* Third rocket deducts 66 cargo, 2 cargoes are removed from cache, ship receives 34 cargoes.

For very low rocket loads, the same logic applies and will not be repeated here. For example, if the individual rocket
load is 1 and p=3, then the first two rockets are “empty” and the third rocket contains 1 cargo.

## Space => Ground

The cargo travels from space to the ground in the following steps:

1. the ground requests x cargo from the ship.
2. the ship receives that request and calculates a target total of about px cargo.
3. the mod first fills the original cargo pod, then tries to create extra cargo pods from the platform hub and launches
   them to the same destination.
4. the ground can therefore receive up to about px cargo while the ship only spends x cargo.

You'll no doubt notice that step 3 creates extra downward cargo pods instead of simply multiplying the inventory in one
pod.

This is the current approximation used by the code. It is closer to “multiple hidden ships are dropping cargo at the
same time” than a pure resource multiplier, but it is still limited by whether extra cargo pods can actually be created.
If you want precise single-pod delivery for valuable items, you can still use a normal-quality Space Platform Hub.

There is also the case where the hub cannot create enough extra cargo pods (for example because the current platform
layout cannot support them at that moment). In that case, the remaining cargo is returned to the hub inventory or kept
in the mod cache instead of being delivered immediately. Building more docking capacity can reduce how often this
happens, but this mod itself does not add extra hatches.

# How to use it

If you've already seen how the multiplier is calculated, then you'll definitely want to upgrade the quality of the Space
Platform Hub.

Unfortunately, there is no way to upgrade the hubs in the original game (they don't fit in the green map, and copying
and pasting doesn't work either). But this is great for this mod, there is no way to change the quality of the hubs and
have the equivalent cargo of the ship increase or decrease out of nowhere. This proves once again that the mod is
“balanced”, doesn't it?

Back to the point, in case you can't upgrade your hubs, you need to make new ships with high quality starter packs. A
new problem arises: it's very difficult to change the quality of space platform hubs in the blueprints (especially if
the hubs are heavily wired).

To solve this problem, I added a button to the bottom right toolbar for modifying the quality of space platform hubs.

* When holding a blueprint, left-clicking on this button will increase the quality of the space platform hubs within the
  blueprint.
* Right clicking on this button while holding a blueprint lowers the quality of the Space Platform Hub within the
  blueprint.

Lastly, if you have any comments or suggestions, let me know
in [Discussion](https://mods.factorio.com/mod/ups_saving_quality_ships/discussion)!

# Acknowledgments

- Special thanks to BAYUNZIYUE. The initial idea of this mod came entirely from him, and I was only responsible for
  writing the specific logic. Meanwhile, we found a series of problems during the use of the mod, and discussed many
  times whether there is a better solution for improvement. Without him, this mod would not be possible.
- Special thanks to plexpt, who told me to go to the forums for help when I was troubled by rocket launches. This was a
  very important node, and it was only by going to the forums that I realized how to write the code for the rocket
  launcher.
- Special thanks to tanvec, who helped me with the documentation and showed me where to start modifying the dynamic
  logistics group, and provided some help on whether the blueprints were modifiable.
- Special thanks to the [BlueprintSignals](https://github.com/JensForstmann/BlueprintSignals/tree/master) project, which
  taught me how to build the buttons in the bottom right corner that handle blueprints.
- Special thanks to PHIDIAS, who provided some code examples for reference in terms of whether blueprints are modifiable
  and how they should be modified.
- Special thanks to everyone who used my mod, and to all the players who made suggestions!

# 模组简介

## 模组效果

* p值（即本模组用来近似模拟多艘同构飞船的倍率）由飞船中心枢纽的品质决定。
* 地面 => 太空：模组会先把飞船请求大致放大到 px，再在货舱落到平台表面后缩减其内容，因此可见的这艘飞船最终大致保留 x 个货物。
* 太空 => 地面：模组会尽量额外创建 cargo pod，让地面最多收到约 px 个货物，而飞船自身只消耗 x 个货物；如果额外 cargo pod 无法创建，剩余货物会回退到 hub 或缓存。

## 它有什么作用？

这个模组是为了优化多艘相同功能飞船同时运行而导致的游戏卡顿问题（常见于游戏后期制作工程基座、钷素科技包时）。如果你的每艘船都是不同功能，那它可能对你影响不大；如果你喜欢将飞船复制粘贴，那它非常适合你！

假定产能、运力不变，如果一艘飞船就能担任之前数艘飞船的职能，那么就可以减少飞船数目，进而达到改善ups的效果。尤其是制作钷素科技包的飞船，它们在破碎边缘飞行时会生成大量星岩，从而导致ups急剧下降。即使你只有一艘这样的飞船，有了这个模组，你的异虫卵消耗、量子处理器消耗、黑瓶产出都会变为之前的p倍，更少时间在破碎边缘运行同样意味着更高的ups。所以这个模组适合任何后期的存档——即使你没有相同功能的飞船。

## 它属于作弊模组吗？

有人可能会问，如果仅仅为了解决星岩过多而导致的卡顿，能不能减少星岩数目，抓到之后再向抓取臂添加数倍星岩？我也想过这个问题，但是我觉得实现它很简单，但是没有那么“平衡”。比如说，星岩数目减少，那么星岩的血量是否也应变为数倍？增加血量的前提下，如果飞船用了大量的爆破火箭弹，爆破火箭弹的伤害是否要翻倍？我认为它很难达到和原版一样的体验。

而这个模组本质上是用一种偏向 UPS 的近似方式，把“多艘同构飞船”压缩成“一艘可见飞船”。它只改写天地货物交互，不会严格复刻多艘真实飞船的全部物理限制（例如它本身不会增加额外接驳口）。所以它更接近“结果等效模拟”，而不是严格的一比一真实模拟。唯一作弊的部分可能是它假装提高了你的电脑配置:)

# 工作原理

## 倍率的计算方式

模拟倍率p与太空平台枢纽的品质有关（也可以说与太空平台启动包的品质有关）。

| 枢纽品质 | 品质等级 | 模拟倍率 |
|:----:|:----:|:----:|
|  普通  |  0   |  1   |
|  精良  |  1   |  2   |
|  稀有  |  2   |  3   |
|  史诗  |  3   |  4   |
|  传说  |  5   |  5   |

之所以传说太空平台枢纽的模拟倍率不是6倍，是因为我发现6倍太难用了，在计算需求时很麻烦。

如果你感兴趣的话，实际使用的计算公式为：

`p = 1 + math.celi(太空平台枢纽品质等级 x 0.79)`

这样，它也能兼容一些扩展品质的模组。

## 地面 => 太空

货物从地面到太空将经历如下几个步骤：

1. 飞船向地面请求 x 个货物（实际上，MOD 会自动生成一个动态物流编组）。
2. 该动态物流编组会让地面侧尝试总共发送约 px 个货物。
3. 每个 cargo pod 落到平台表面后，MOD 会检查其库存，并移除约 (p-1)/p 的内容（具体由下面的缓存逻辑处理零头）。
4. 可见的这艘飞船最终大致保留 x 个货物。

也就是说，这个方向的实现方式是“放大请求 + 在货舱到达后缩货”。它追求的是总体吞吐结果接近多艘同构飞船，而不是宣称一艘可见飞船已经拥有了 p 艘飞船那样的接收接口数。

你肯定会注意到，步骤3的处理是最棘手的，尤其是以下情况：

* 单个火箭的货物不是p的倍数怎么办？
* 火箭载荷极小的货物（例如火箭载荷为1）怎么办？

不用担心，这个模组提供了一个不可见的缓存区，用于应对这种情况。

简单来讲，多扣除的部分会添加到缓存区，并在下次运输相同物品/品质时重新利用。

例如单个火箭载荷为100，p=3，那么：

* 第一发火箭扣除67个货物，缓存区添加1个货物，飞船收到33个货物
* 第二发火箭扣除67个货物，缓存区添加1个货物，飞船收到33个货物
* 第三发火箭扣除66个货物，缓存区移除2个货物，飞船收到34个货物

对于火箭载荷极低的情况，也是同样的处理逻辑，在此不再赘述。例如单个火箭载荷为1，p=3，那么前两发火箭都为“空火箭”，第三发火箭包含1个货物。

## 太空 => 地面

货物从太空到地面将经历如下几个步骤：

1. 地面向飞船请求 x 个货物。
2. 飞船收到请求后，会计算一个约 px 的目标总量。
3. MOD 会先往原有 cargo pod 中塞货；如果装不下，就继续从平台 hub 创建额外的 cargo pod，并把它们发往同一个目的地。
4. 因此地面最多可以收到约 px 个货物，而飞船自身只消耗 x 个货物。

你肯定会注意到，步骤 3 不是简单修改一个货舱里的数值，而是尝试真正创建额外的下行 cargo pod。

这是当前代码采用的近似方案。和单纯把资源倍率相乘相比，它更接近“多艘隐藏飞船同时向下投货”的效果；但它是否能完全达到目标，还取决于额外 cargo pod 当时能否被成功创建。实际上，你完全可以使用普通品质的太空平台枢纽，来运输一些较为珍贵的物品，以精确投放。

另外，步骤 3 还可能出现“额外 cargo pod 创建不足”的情况；这时，原本计划向下投放的剩余货物会回退到 hub 库存或缓存，而不会立刻送达。增加停靠/接驳能力可以减少这种情况，但本模组本身不会额外增加接驳口。

# 如何使用

如果你已经看完倍率的计算方式，那么你一定想将升级太空平台枢纽的品质。

很遗憾，原版游戏没有升级枢纽的方法（枢纽无法放入绿图，复制粘贴也不行）。但这对于这个模组来讲实在是太棒了，不会出现枢纽品质变化而导致飞船的等效货物凭空增多或减少的情况。这再一次证明了这个模组很“平衡”，不是吗？

回归正题，在无法升级枢纽的情况下，你需要用高品质启动包制作新的飞船。此时又出现了新的问题：蓝图中的太空平台枢纽品质很难更换（尤其是枢纽大量连线的情况下）。

为了解决这个问题，我在右下角工具栏加了一个按钮，用于修改太空平台枢纽的品质。

* 手持蓝图时，左键点击该按钮可以提高蓝图内太空平台枢纽的品质。
* 手持蓝图时，右键点击该按钮可以降低蓝图内太空平台枢纽的品质。

最后，如果你有任何意见或建议，欢迎在[讨论区](https://mods.factorio.com/mod/ups_saving_quality_ships/discussion)告诉我！

# 致谢

- 特别感谢BAYUNZIYUE。这个模组最初的构思完全来源于他，我只是负责编写具体逻辑。同时，在模组使用过程中我们发现了一系列问题，并多次讨论是否有更好的改进方案。可以说，没有他就没有这个模组。
- 特别感谢plexpt。在我被火箭发射困扰的时候，他告诉我可以去论坛寻求帮助。这是很重要的节点，去论坛查阅相关资料我才明白了火箭发射的代码应该如何编写。
- 特别感谢tanvec。他帮助我查阅文档，指明动态物流编组应该从哪里开始修改，并对蓝图是否可修改提供了一些帮助。
- 特别感谢[BlueprintSignals](https://github.com/JensForstmann/BlueprintSignals/tree/master)项目，它教会了我如何在右下角构建处理蓝图的按钮。
- 特别感谢PHIDIAS。在蓝图是否可修改、应该如何修改的方面，他提供了一些代码示例作为参考。
- 特别感谢使用我模组的每一位玩家，以及所有提出建议的玩家！
