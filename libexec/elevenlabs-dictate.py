#!/usr/bin/env python3
"""Headless toggle recording; OSTT transcription is typed via Wayland."""
import os,pathlib,signal,subprocess,time,shutil
root=pathlib.Path(os.environ['RUNTIME_DIRECTORY'])

def notify(message):
    subprocess.run(['notify-send','-r','92419','-t','2500','Dictation',message],check=False)

def main():
    audio=root/'recording.wav'
    transcript=root/'transcript.txt'
    recorder=subprocess.Popen(['pw-record','--rate','16000','--channels','1',str(audio)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        notify('Recording — press F9 or Alt+D again to finish')
        start=time.monotonic()
        while not (root/'stop').exists():
            time.sleep(.05)
            if recorder.poll() is not None: raise RuntimeError('Microphone recording failed.')
            if time.monotonic()-start>600:break
        recorder.send_signal(signal.SIGINT)
        recorder.wait(timeout=10)
    finally:
        if recorder.poll() is None:
            recorder.terminate();recorder.wait(timeout=5)
    if not audio.exists() or audio.stat().st_size<3200:
        notify('Recording was too short.');return
    notify('Transcribing…')
    result=subprocess.run([shutil.which('ostt') or str(pathlib.Path.home()/'.local/bin/ostt'),'transcribe',str(audio),'-m','elevenlabs/scribe_v2','-o',str(transcript)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=120)
    if result.returncode or not transcript.exists(): raise RuntimeError('Transcription failed. Check ElevenLabs access or connection.')
    text=transcript.read_text().strip()
    if not text:notify('No speech detected.');return
    subprocess.run(['wtype','-'],input=text,text=True,check=True,timeout=60)
    notify('Transcript typed')

try:main()
except (RuntimeError,subprocess.SubprocessError,OSError) as error:
    notify(str(error) if isinstance(error,RuntimeError) else 'Dictation failed. Try again.')
    raise SystemExit(1)
finally:
    for file in root.glob('*'):
        if file.is_file():file.unlink(missing_ok=True)
