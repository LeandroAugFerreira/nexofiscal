"""Vídeos no padrão do portfólio: voz contínua, mascote e legendas externas PT/EN.

Requer Pillow, NumPy, edge-tts e FFmpeg. Configure FITNOTA_VIDEO_TOOLS se
edge-tts estiver instalado em um diretório de ferramentas separado.
"""
import argparse
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import wave

if os.environ.get('FITNOTA_VIDEO_TOOLS'):
    sys.path.insert(0, os.environ['FITNOTA_VIDEO_TOOLS'])
import edge_tts
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.tmp/portfolio-video'
OUTPUT = ROOT / 'output/video'
FPS = 24
VOICE = 'pt-BR-AntonioNeural'


def run(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def normalized(text):
    return ''.join(c.lower() for c in text if c.isalnum())


async def audio(kind, chapters):
    spoken = ' '.join(chapter['pt'] for chapter in chapters)
    digest = hashlib.sha256((spoken + VOICE + '+3%-2Hz').encode()).hexdigest()
    marker, target = WORK / (kind + '.sha256'), WORK / (kind + '.mp3')
    metadata = WORK / (kind + '.words.json')
    if not (target.exists() and metadata.exists() and marker.exists() and marker.read_text() == digest):
        words = []
        communication = edge_tts.Communicate(spoken, VOICE, rate='+3%', pitch='-2Hz', boundary='WordBoundary')
        with target.open('wb') as stream:
            async for chunk in communication.stream():
                if chunk['type'] == 'audio':
                    stream.write(chunk['data'])
                elif chunk['type'] == 'WordBoundary':
                    words.append({'text': chunk['text'], 'start': chunk['offset'] / 1e7,
                                  'end': (chunk['offset'] + chunk['duration']) / 1e7})
        assert words and target.stat().st_size > 1000
        metadata.write_text(json.dumps(words, ensure_ascii=False), encoding='utf-8')
        marker.write_text(digest)
    pcm = WORK / (kind + '.wav')
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(target), '-ar', '24000', '-ac', '1', str(pcm)])
    with wave.open(str(pcm), 'rb') as source:
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(np.float32) / 32768
        duration = len(samples) / source.getframerate()
    words = json.loads(metadata.read_text(encoding='utf-8'))
    compact = normalized(spoken)
    assert ''.join(normalized(word['text']) for word in words) == compact, 'Alinhamento das palavras não corresponde à narração.'
    cursor = 0
    for word in words:
        word['position'] = cursor
        cursor += len(normalized(word['text']))
    cursor, timeline = 0, []
    for chapter in chapters:
        end = cursor + len(normalized(chapter['pt']))
        selected = [word for word in words if cursor <= word['position'] < end]
        timeline.append({**chapter, 'start': selected[0]['start'], 'end': selected[-1]['end']})
        cursor = end
    for index, chapter in enumerate(timeline):
        chapter['scene_start'] = 0 if index == 0 else (timeline[index - 1]['end'] + chapter['start']) / 2
    return timeline, samples, duration


def timestamp(value):
    ms = round(value * 1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'


def captions(kind, chapters):
    for language in ('pt', 'en'):
        lines = ['WEBVTT', '']
        for index, chapter in enumerate(chapters, 1):
            lines.extend([str(index), f"{timestamp(chapter['start'])} --> {timestamp(chapter['end'])}", chapter[language], ''])
        (OUTPUT / f'nexofiscal-{kind}-{language}.vtt').write_text('\n'.join(lines), encoding='utf-8')


def render(kind, chapters, samples, duration, mascot_path):
    size = (1280, 720)
    frames = []
    for chapter in chapters:
        screenshot = Image.open(ROOT / 'artifacts/portfolio-demo' / (chapter['image'] + '.png')).convert('RGB')
        screenshot.thumbnail(size, Image.Resampling.LANCZOS)
        frame = Image.new('RGB', size, '#04101e')
        frame.paste(screenshot, ((size[0] - screenshot.width) // 2, (size[1] - screenshot.height) // 2))
        frames.append(frame)
    mascot = Image.open(mascot_path).convert('RGBA')
    mascot.thumbnail((500, 243), Image.Resampling.LANCZOS)
    position = (12, 720 - mascot.height - 10)
    destination = OUTPUT / f'nexofiscal-{kind}.mp4'
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', '1280x720', '-r', str(FPS), '-i', '-', '-i', str(WORK / (kind + '.wav')),
               '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
               '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
               '-t', str(duration), '-movflags', '+faststart', str(destination)]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        index = 0
        for number in range(math.ceil(duration * FPS)):
            time = number / FPS
            while index + 1 < len(chapters) and time >= chapters[index + 1]['scene_start']:
                index += 1
            frame = frames[index].copy()
            frame.paste(mascot, position, mascot)
            segment = samples[int(time * 24000):int((time + 1/FPS) * 24000)]
            level = min(1.0, float(np.sqrt(np.mean(segment ** 2))) * 6) if len(segment) else 0
            draw = ImageDraw.Draw(frame)
            x = position[0] + round(mascot.width * .415)
            y = position[1] + round(mascot.height * .265)
            for bar in range(5):
                height = 1 + round(level * (3 + 3 * abs(math.sin(number * .7 + bar))))
                draw.rounded_rectangle((x - 8 + bar * 4, y - height/2, x - 6 + bar * 4, y + height/2), radius=1, fill='#38e4ff')
            encoder.stdin.write(frame.tobytes())
            if number == round(FPS * 2):
                frame.save(OUTPUT / f'nexofiscal-{kind}-preview.jpg', quality=94)
        encoder.stdin.close()
        assert encoder.wait() == 0
    finally:
        if encoder.poll() is None:
            encoder.terminate()
    scenes = [{'start': chapter['scene_start'], 'end': chapters[index+1]['scene_start'] if index+1 < len(chapters) else duration,
               'title': chapter['title']} for index, chapter in enumerate(chapters)]
    (OUTPUT / f'nexofiscal-{kind}-cenas.json').write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding='utf-8')
    captions(kind, chapters)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio-only', action='store_true')
    parser.add_argument('--mascot', type=Path, default=ROOT.parent / 'portfolio/img/transcricao/mascote-vox.png')
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    specs = json.loads((ROOT / 'docs/roteiro-portfolio.json').read_text(encoding='utf-8'))
    report = {}
    for kind, chapters in specs.items():
        timeline, samples, duration = await audio(kind, chapters)
        if not args.audio_only:
            render(kind, timeline, samples, duration, args.mascot)
        report[kind] = {'duration': duration, 'voice': VOICE, 'rate': '+3%', 'pitch': '-2Hz', 'continuous_audio': True}
        print(f'{kind}: {duration:.1f}s; voz contínua PT-BR e legendas PT/EN.', flush=True)
    (WORK / 'narracao.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    asyncio.run(main())
