# Ubiquitous Language

本文件记录仓库内长期使用的领域术语。术语应来自现有代码、文档、配置、UI 文案或用户确认；含义不清楚时先标为待确认。

## Factorio Runtime

- 太空平台 / Space Platform：Factorio Space Age 的飞船平台，运行时代码中通常对应 `LuaSpacePlatform`。
- 平台枢纽 / Hub：太空平台中心实体，代码中通常通过 `platform.hub` 访问，用于读取库存、物流编组和品质。
- 货舱 / Cargo Pod：平台与地面之间运输物品的运行时实体，代码中通常对应 `cargo-pod`。
- 物流编组 / Logistic Section：平台枢纽物流请求中的编组，代码中通过 `hub.get_logistic_sections()` 读取和维护。
- 自动物流编组 / Auto Logistic Section：`ups_saving_quality_ships` 自动创建的物流编组，用于补足品质飞船模拟倍率带来的额外请求。
- 平台缓存 / Platform Cache：`ups_saving_quality_ships/src/scripts/platform_cache.lua` 维护的运行时平台索引和轮询批次缓存。
- 失效运行时对象 / Invalid Runtime Object：Factorio 运行时对象被删除或失效后的状态；访问除 `valid` 以外的字段前必须先确认对象有效。

## UPS Saving Quality Ships

- 模拟倍率 / Simulation Multiplier：`ups_saving_quality_ships` 根据平台枢纽品质计算的货运倍率，当前逻辑为品质等级加一。
- 上行投送 / Upward Delivery：从地面火箭发射井向太空平台发送货物。
- 下行投送 / Downward Delivery：从太空平台向地面或接收站投放货物。
