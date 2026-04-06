local constants = {
  CRAFTING_FINISHED_SOUND = "autocraft-core-crafting_finished",
  AUTOCRAFT_WRENCH_SIGNAL_NAME = "signal-autocraft-wrench",
  AUTOCRAFT_SHORTCUT_NAME = "autocraft-toggle",
  AUTOCRAFT_SOUND_ENABLED = "autocraft-sound-enabled",
  AUTOCRAFT_PREFIX_SETTING = "autocraft-wrench-prefix",
  AUTOCRAFT_MATCH_MODE_SETTING = "autocraft-match-mode",
  AUTOCRAFT_DEFAULT_ENABLED = true,
  AUTOCRAFT_MATCH_MODE_FULL = "full-match",
  AUTOCRAFT_MATCH_MODE_PREFIX = "prefix",
  AUTOCRAFT_MATCH_MODE_PLAYER_NAME = "player-name",
  AUTOCRAFT_MATCH_MODE_PREFIX_AND_PLAYER_NAME = "prefix-player-name",
  AUTOCRAFT_MISSING_SECTION_TAG = "missing-materials",
}

constants.AUTOCRAFT_DEFAULT_PREFIX_RICH_TEXT = "[virtual-signal=" .. constants.AUTOCRAFT_WRENCH_SIGNAL_NAME .. "]"

return constants
