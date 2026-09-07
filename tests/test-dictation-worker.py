#!/usr/bin/env python3
"""Exercise recording stop and typed output without hardware, network or clipboard."""
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

WORKER = Path(__file__).resolve().parents[1] / 'libexec/elevenlabs-dictate.py'

class Dictation(unittest.TestCase):
    def test_release_transcribes_and_types_without_clipboard(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / 'runtime'; runtime.mkdir()
            tools = root / 'bin'; tools.mkdir()
            programs = {
                'notify-send': '#!/bin/sh\nexit 0\n',
                'pw-record': '''#!/usr/bin/python3
import pathlib,signal,sys,time
signal.signal(signal.SIGINT,lambda *_:sys.exit(0))
pathlib.Path(sys.argv[-1]).write_bytes(b'x'*4000)
while True:time.sleep(.01)
''',
                'ostt': '''#!/usr/bin/python3
import pathlib,sys
assert sys.argv[1]=='transcribe'
assert sys.argv[sys.argv.index('-m')+1]=='elevenlabs/scribe_v2'
pathlib.Path(sys.argv[sys.argv.index('-o')+1]).write_text('Test dictation')
''',
                'wtype': '''#!/usr/bin/python3
import pathlib,sys,os
assert sys.argv[1:]==['-']
pathlib.Path(os.environ['TYPED_OUTPUT']).write_text(sys.stdin.read())
''',
            }
            for name, body in programs.items():
                path = tools / name; path.write_text(body); path.chmod(0o755)
            env = dict(os.environ, PATH=str(tools), RUNTIME_DIRECTORY=str(runtime), TYPED_OUTPUT=str(root/'typed'))
            process = subprocess.Popen(['/usr/bin/python3', str(WORKER)], env=env)
            try:
                deadline = time.monotonic()+5
                while not (runtime/'recording.wav').exists():
                    if time.monotonic()>deadline: self.fail('Recorder did not start')
                    time.sleep(.01)
                self.assertFalse((root/'typed').exists())
                (runtime/'stop').touch()
                self.assertEqual(process.wait(timeout=5), 0)
                self.assertEqual((root/'typed').read_text(), 'Test dictation')
                self.assertEqual(list(runtime.iterdir()), [])
            finally:
                if process.poll() is None: process.kill(); process.wait()

if __name__ == '__main__': unittest.main()
