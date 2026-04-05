import type { PrototypeData } from "factorio:common";
import type { SoundDefinitionStruct, SoundStruct } from "factorio:prototype";

declare const data: PrototypeData;

const crafting_finished = data.raw["utility-sounds"]["default"]?.crafting_finished;

if (crafting_finished) {
  if (Array.isArray(crafting_finished)) {
    (crafting_finished as SoundDefinitionStruct[])[0].volume = 0;
  } else {
    (crafting_finished as SoundStruct).volume = 0;
  }
}
