#!/bin/bash
set -euo pipefail
project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
export OMARCHY_T2_ROOT="$test_dir/root"
export HOME="$test_dir/home"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_STATE_HOME="$HOME/.local/state"
mkdir -p "$OMARCHY_T2_ROOT/etc" "$OMARCHY_T2_ROOT/sys/devices/platform/APP0001:00" "$XDG_CONFIG_HOME/omarchy-t2"
printf 'BATTERY_LIMIT=95\nFAN_PROFILE=cool\nPOWER_ENABLED=true\n' >"$OMARCHY_T2_ROOT/etc/omarchy-t2.conf"
printf 'KEYBOARD_LAYOUT=de\nTAP_TO_CLICK=false\nTTS_ENABLED=true\n' >"$XDG_CONFIG_HOME/omarchy-t2/config"
printf '100\n' >"$OMARCHY_T2_ROOT/sys/devices/platform/APP0001:00/battery_charge_limit"
cp "$project_dir/config/t2fand-quiet.conf" "$OMARCHY_T2_ROOT/etc/t2fand.conf"
source "$project_dir/bin/omarchy-t2" help >/dev/null
require_supported_model() { return 0; }
mkdir -p "$test_dir/share/fan"
cp "$project_dir"/config/t2fand-*.conf "$test_dir/share/fan/"
SHARE_DIR="$test_dir/share"
# Mock only read-only runtime queries; never access the host session.
runtime() { return 0; }
query_failure=false
live_service=inactive
live_tts=false
live_audio=false
systemctl_calls=
systemctl() {
  case $1 in
    show)
      [[ $query_failure == false ]] || return 1
      echo "$live_service"
      ;;
    is-active) [[ $live_service == active ]] ;;
    daemon-reload|restart) systemctl_calls+="$1 ${*:2}"$'\n' ;;
    *) return 1 ;;
  esac
}
sudo() { "$@"; }
hyprctl() {
  [[ $query_failure == false ]] || return 1
  case "$2 ${3:-}" in
    'getoption input:kb_layout') echo '{"str":"us"}' ;;
    'getoption input:kb_variant') echo '{"str":"mac-iso"}' ;;
    'getoption input:touchpad:tap-to-click') echo '{"bool":true}' ;;
    'binds ') if $live_tts; then echo '[{"arg":"omarchy-tts read"}]'; else echo '[]'; fi ;;
    *) return 1 ;;
  esac
}
pactl() {
  [[ $query_failure == false ]] || return 1
  if $live_audio; then
    echo '1 effect_input.filter-chain-speakers PipeWire SUSPENDED'
    echo '2 effect_output.filter-chain-t2-mic PipeWire SUSPENDED'
  fi
}
assert_line() { grep -Fxq "$1" <<<"$status" || { echo "Missing: $1" >&2; echo "$status" >&2; exit 1; }; }
status=$(cmd_status)
assert_line 'Battery limit:  100%'
assert_line 'Fan profile:    quiet (installed config; service: inactive)'
assert_line 'Power policy:   inactive'
assert_line 'Keyboard:       us/mac-iso'
assert_line 'Tap-to-click:   true'
assert_line 'Text-to-speech: disabled (bindings; models: missing; engine: missing)'
assert_line 'Speaker DSP:    inactive'
assert_line 'Microphone DSP: inactive'
[[ $(cmd_battery status) == 100 ]]
[[ $(cmd_input status) == 'keyboard=us/mac-iso tap=true' ]]
live_service=active
live_tts=true
live_audio=true
status=$(cmd_status)
assert_line 'Power policy:   active'
assert_line 'Text-to-speech: enabled (bindings; models: missing; engine: missing)'
assert_line 'Speaker DSP:    active'
assert_line 'Microphone DSP: active'
query_failure=true
status=$(cmd_status)
assert_line 'Power policy:   unavailable'
assert_line 'Keyboard:       unavailable'
assert_line 'Tap-to-click:   unavailable'
assert_line 'Speaker DSP:    unavailable'
# Missing hardware must not fall back to the stale saved limit.
rm "$OMARCHY_T2_ROOT/sys/devices/platform/APP0001:00/battery_charge_limit"
[[ $(battery_actual_limit) == unavailable ]]

live_service=inactive
warning_file="$test_dir/power-warning"
power_restart 2>"$warning_file"
grep -Fq "run 'omarchy-t2 power enable' to apply them" "$warning_file"
[[ $systemctl_calls != *restart* ]]

live_service=active
systemctl_calls=
power_restart 2>"$warning_file"
[[ ! -s $warning_file ]]
grep -Fxq 'restart power-optimizer.service' <<<"$systemctl_calls"
echo 'All live status tests passed'
