#!/bin/bash
set -euo pipefail
project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
export HOME="$test_dir/home"
export XDG_CONFIG_HOME="$HOME/.config" XDG_STATE_HOME="$HOME/.local/state" XDG_DATA_HOME="$HOME/.local/share"
export OMARCHY_T2_ROOT="$test_dir/root" OMARCHY_T2_SKIP_RUNTIME=true
export OMARCHY_T2_SHARE_DIR="$project_dir/config"
mkdir -p "$XDG_CONFIG_HOME/hypr" "$test_dir/share/defaults"
printf '%s\n' '-- Existing configuration' > "$XDG_CONFIG_HOME/hypr/hyprland.lua"
cp "$project_dir/config/input.conf" "$test_dir/share/defaults/input.conf"
source "$project_dir/bin/omarchy-t2" help >/dev/null
SHARE_DIR="$test_dir/share"
require_supported_model() { :; }
cloud_voice_require() { :; }
module="$XDG_CONFIG_HOME/hypr/omarchy-t2.lua"
cmd_tts setup --provider elevenlabs --yes --dry-run
[[ ! -e $module && ! -e $USER_CONFIG ]]
DRY_RUN=false
cmd_tts setup --provider elevenlabs --yes
cmd_stt setup --yes
[[ $(grep -c '^require("hypr.omarchy-t2")' "$XDG_CONFIG_HOME/hypr/hyprland.lua") == 1 ]]
grep -Fq '"omarchy-elevenlabs-read"' "$module"
grep -Fq 'o.bind("F9", "Start or stop dictation", "omarchy-elevenlabs-dictate toggle")' "$module"
grep -Fq 'o.bind("ALT + D", "Start or stop dictation", "omarchy-elevenlabs-dictate toggle")' "$module"
grep -Fq 'TTS_PROVIDER=elevenlabs' "$USER_CONFIG"
grep -Fq 'STT_ENABLED=true' "$USER_CONFIG"
# Switching to Qwen must preserve independently enabled dictation.
write_setting "$USER_CONFIG" TTS_PROVIDER qwen user
input_apply
grep -Fq '"omarchy-tts read"' "$module"
grep -Fq 'if true then' "$module"
cmd_stt disable
load_input_config
[[ $TTS_ENABLED == true && $STT_ENABLED == false && $TTS_PROVIDER == qwen ]]
cmd_tts disable
load_input_config
[[ $TTS_ENABLED == false ]]
[[ ! -e $XDG_DATA_HOME/ostt/credentials ]]
echo 'Cloud voice configuration tests passed'
