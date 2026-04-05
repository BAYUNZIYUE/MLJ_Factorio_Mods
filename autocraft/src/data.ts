import type { PrototypeData } from "factorio:common";
import type {
  SoundPrototype,
  ShortcutPrototype,
  SoundDefinitionStruct,
  SoundStruct,
} from "factorio:prototype";
import { CRAFTING_FINISHED_SOUND, SHORTCUT_NAME } from "./constants";

declare const data: PrototypeData;

const sound = data.raw["utility-sounds"]["default"]?.crafting_finished;

let crafting_finished: SoundStruct | SoundDefinitionStruct | undefined = undefined;
if (sound) {
  if (Array.isArray(sound)) {
    crafting_finished = (sound as SoundDefinitionStruct[])[0];
  } else {
    crafting_finished = sound as SoundStruct;
  }
}

data.extend([
  {
    type: "sound",
    name: CRAFTING_FINISHED_SOUND,
    filename: crafting_finished?.filename ?? "__core__/sound/crafting-finished.ogg",
    volume: crafting_finished?.volume ?? 0.75,
  } satisfies SoundPrototype,
  {
    type: "shortcut",
    name: SHORTCUT_NAME,
    action: "lua",
    toggleable: true,
    icon: "__autocraft-logistics__/graphics/icon/32.png",
    icon_size: 32,
    small_icon: "__autocraft-logistics__/graphics/icon/24.png",
    small_icon_size: 24,
  } satisfies ShortcutPrototype,
]);
