#!/usr/bin/env python3
"""Read Wayland primary selection using the locally configured ElevenLabs key."""
import json, os, pathlib, subprocess, sys, tempfile
from elevenlabs_auth import credentials
import urllib.request, urllib.error, urllib.parse

HOME = pathlib.Path.home()

def notify(message):
    subprocess.run(['notify-send', 'Read aloud', message], check=False)


def synthesize(text, target):
    settings = pathlib.Path(os.environ.get('XDG_CONFIG_HOME', HOME / '.config')) / 'omarchy-t2/elevenlabs-voice.json'
    config = json.loads(settings.read_text()) if settings.exists() else {}
    voice = config.get('voice', 'JBFqnCBsd6RMkjVDRZzb')
    model = config.get('model', 'eleven_flash_v2_5')
    url = 'https://api.elevenlabs.io/v1/text-to-speech/' + urllib.parse.quote(voice, safe='') + '?output_format=mp3_44100_128'
    req = urllib.request.Request(url, data=json.dumps({'text': text, 'model_id': model}).encode(),
        headers={'xi-api-key': credentials(), 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'})
    with urllib.request.urlopen(req, timeout=60) as response:
        with open(target, 'wb') as output:
            while chunk := response.read(65536): output.write(chunk)

def main():
    if '--test' in sys.argv:
        text = 'ElevenLabs read aloud is ready.'
    else:
        cmd = ['wl-paste', '--no-newline', '--type', 'text']
        if '--clipboard' not in sys.argv: cmd.append('--primary')
        result = subprocess.run(cmd, capture_output=True, timeout=3)
        text = result.stdout.decode('utf-8', errors='replace').strip() if result.returncode == 0 else ''
    if not text:
        raise ValueError('Select some text first. If the app does not expose selections, copy it and use Option+Shift+R.')
    # Sequential chunks support long selections without exceeding model limits.
    chunks = []
    while text:
        end = min(len(text), 4000)
        if end < len(text):
            split = text.rfind(' ', 0, end)
            if split > 2000: end = split
        chunks.append(text[:end]); text = text[end:].lstrip()
    notify('Preparing speech… Option+E pauses or resumes.')
    with tempfile.TemporaryDirectory(prefix='elevenlabs-read-', dir=os.environ['RUNTIME_DIRECTORY']) as directory:
        for i, chunk in enumerate(chunks):
            audio = pathlib.Path(directory) / f'{i}.mp3'
            synthesize(chunk, audio)
            subprocess.run(['mpv', '--no-config', '--no-video', '--really-quiet', str(audio)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            audio.unlink()
    if '--test' in sys.argv: print('ElevenLabs synthesis and playback succeeded.')

if __name__ == '__main__':
    try: main()
    except urllib.error.HTTPError as error:
        print(f'ElevenLabs HTTP {error.code}', file=sys.stderr)
        notify(f'ElevenLabs returned HTTP {error.code}. Check key permissions and available credits.')
        sys.exit(1)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        notify(str(error) if isinstance(error, ValueError) else 'Could not read text or play speech. Try again.')
        sys.exit(1)
