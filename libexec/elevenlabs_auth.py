#!/usr/bin/env python3
"""Private ElevenLabs credentials shared by TTS and OSTT; never print keys."""
import getpass
import json
import os
from pathlib import Path
import tempfile
import tomllib


def credential_path():
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'ostt/credentials'


def credentials():
    path = credential_path()
    if path.exists():
        key = tomllib.loads(path.read_text()).get('elevenlabs')
        if key:
            return key
    raise ValueError('Run omarchy-t2 tts auth (or ostt auth login elevenlabs) first.')


def save_key(key):
    if not key or any(ord(c) < 32 for c in key):
        raise ValueError('Enter a nonempty API key without control characters.')
    path = credential_path()
    data = tomllib.loads(path.read_text()) if path.exists() else {}
    data['elevenlabs'] = key
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            for name, value in data.items():
                output.write(f'{json.dumps(name)} = {json.dumps(value)}\n')
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


if __name__ == '__main__':
    try:
        save_key(getpass.getpass('ElevenLabs API key (hidden): ').strip())
        print('ElevenLabs key saved privately for TTS and speech-to-text.')
    except (ValueError, OSError, EOFError, KeyboardInterrupt) as error:
        raise SystemExit('Credential setup failed; no key was displayed.') from None
