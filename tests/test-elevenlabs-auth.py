#!/usr/bin/env python3
import importlib.util
import os
from pathlib import Path
import tempfile
import tomllib
import unittest

spec = importlib.util.spec_from_file_location('auth', Path(__file__).resolve().parents[1] / 'libexec/elevenlabs_auth.py')
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)

class Credentials(unittest.TestCase):
    def test_private_shared_store_and_preserved_providers(self):
        with tempfile.TemporaryDirectory() as directory:
            old = os.environ.get('XDG_DATA_HOME')
            os.environ['XDG_DATA_HOME'] = directory
            try:
                path = auth.credential_path()
                path.parent.mkdir(parents=True)
                path.write_text('other = "existing-test-value"\n')
                auth.save_key('fake-test-credential')
                self.assertEqual(auth.credentials(), 'fake-test-credential')
                self.assertEqual(tomllib.loads(path.read_text())['other'], 'existing-test-value')
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                before = path.read_bytes()
                with self.assertRaises(ValueError): auth.save_key('')
                self.assertEqual(path.read_bytes(), before)
            finally:
                if old is None: os.environ.pop('XDG_DATA_HOME', None)
                else: os.environ['XDG_DATA_HOME'] = old

if __name__ == '__main__': unittest.main()
