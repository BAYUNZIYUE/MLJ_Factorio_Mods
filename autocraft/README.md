# Autocraft

A [Factorio](https://factorio.com/) mod for automatically hand-crafting items based on
a logistics section called `Autocraft`. You can leave the section disabled (so that logistics bots
don't try to bring you the items) and Autocraft will still build them. You can leave the section
enabled and Autocraft will build items until Autocraft or bots satisfy the requests. Set the
minimum to however many of the item you want to have in your inventory and Autocraft will build them.

Make sure to enable the shortcut to start crafting. If you want to stop, just disable the shortcut.
Cancelling an item in the crafting queue added by Autocraft will disable the shortcut. Re-enable
it when you are ready!

## Download

Download on the [Factorio mod portal](https://mods.factorio.com/mod/autocraft-logistics),
either on the website or in-game.

## Screenshots

TODO: take screenshots

# Contributing

Autocraft is written in TypeScript and compiled to Lua with [TypeScriptToLua](https://typescripttolua.github.io/).
Typings are provided by [typed-factorio](https://github.com/GlassBricks/typed-factorio).

Debugging can be done with [Factorio Modding Tool Kit](https://github.com/justarandomgeek/vscode-factoriomod-debug).

```bash
# install dependencies
npm install

# start watching
npm run dev

# build a release you can drop into your mods folder
npm run release
```

# Icons

This project includes icons from Flaticon, which are licensed under their respective licenses.

- <a href="https://www.flaticon.com/free-icons/busy" title="busy icons">Thumbnail icon created by noomtah - Flaticon</a>
- <a href="https://www.flaticon.com/free-icons/automation" title="automation icons">Shortcut icons created by Freepik - Flaticon</a>
