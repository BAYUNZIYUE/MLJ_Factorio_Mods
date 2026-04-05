import type { SettingsData } from "factorio:common";
import type { BoolSettingDefinition } from "factorio:settings";
import { AUTOCRAFT_SOUND_ENABLED } from "./constants";

declare const data: SettingsData;

data.extend([
  {
    type: "bool-setting",
    name: AUTOCRAFT_SOUND_ENABLED,
    setting_type: "runtime-per-user",
    default_value: false,
  } satisfies BoolSettingDefinition,
]);
