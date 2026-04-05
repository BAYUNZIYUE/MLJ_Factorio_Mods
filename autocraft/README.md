# Autocraft

A [Factorio](https://factorio.com/) mod for automatically hand-crafting items based on
a logistics section named `Autocraft-<player name>`. When that section is active, Autocraft
automatically hand-crafts missing items for the current player. It can also include other active
logistics sections when the `Existing sections use autocraft` runtime-per-user setting is enabled.

Missing amount is calculated from the combined section requests, then reduced by:

- items already in the player's inventory
- items already present in the current logistic network
- items already queued for hand crafting

## Download

Download on the [Factorio mod portal](https://mods.factorio.com/mod/autocraft-logistics),
either on the website or in-game.

## Screenshots

TODO: take screenshots

# Development

Autocraft now lives directly as Lua source under `src/`.

```bash
# package all mods in this workspace
python3 pack_mods.py
```

For hot-reload style debugging, extract the packaged mod folder (the archive root directory, not
`src/`) into `%AppData%\Factorio\mods` and remove any older zip or folder version of the same mod
before launching the game.

# Icons

This project includes icons from Flaticon, which are licensed under their respective licenses.

- <a href="https://www.flaticon.com/free-icons/busy" title="busy icons">Thumbnail icon created by noomtah - Flaticon</a>
- <a href="https://www.flaticon.com/free-icons/automation" title="automation icons">Shortcut icons created by Freepik - Flaticon</a>
