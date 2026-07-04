"""Deterministic placeholder media generation for M2."""

from __future__ import annotations

import hashlib
import io
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from models import Scene

STORYBOARD_WIDTH = 1280
STORYBOARD_HEIGHT = 720
CLIP_DURATION_SECONDS = 3
NARRATION_SAMPLE_RATE = 22050


@dataclass(frozen=True)
class PlaceholderAsset:
    role: str
    filename: str
    data: bytes
    content_type: str
    generator: str = "placeholder"
    playable: bool = True


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scene_color(scene_id: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(scene_id.encode()).hexdigest()
    return (
        int(digest[0:2], 16),
        int(digest[2:4], 16),
        int(digest[4:6], 16),
    )


def _load_font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def generate_storyboard_png(scene: Scene) -> PlaceholderAsset:
    bg = scene_color(scene.scene_id)
    accent = scene_color(f"{scene.scene_id}:accent")
    image = Image.new("RGB", (STORYBOARD_WIDTH, STORYBOARD_HEIGHT), bg)
    draw = ImageDraw.Draw(image)

    title_font = _load_font(48)
    body_font = _load_font(28)
    meta_font = _load_font(22)

    draw.rectangle(
        (40, 40, STORYBOARD_WIDTH - 40, STORYBOARD_HEIGHT - 40),
        outline=accent,
        width=4,
    )
    draw.text((80, 80), scene.title, fill="white", font=title_font)

    narration_preview = scene.narration[:80]
    if len(scene.narration) > 80:
        narration_preview += "…"
    draw.text((80, 160), narration_preview, fill="white", font=body_font)

    chunk_line = f"Chunks: {', '.join(scene.source_chunk_ids)}"
    draw.text((80, STORYBOARD_HEIGHT - 100), chunk_line, fill=accent, font=meta_font)
    draw.text(
        (80, STORYBOARD_HEIGHT - 60),
        f"Scene: {scene.scene_id}",
        fill="white",
        font=meta_font,
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    data = buffer.getvalue()
    return PlaceholderAsset(
        role="storyboard",
        filename="storyboard.png",
        data=data,
        content_type="image/png",
    )


def generate_narration_wav(scene: Scene) -> PlaceholderAsset:
    num_frames = NARRATION_SAMPLE_RATE * CLIP_DURATION_SECONDS
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(NARRATION_SAMPLE_RATE)
        wav_file.writeframes(b"\x00\x00" * num_frames)
    return PlaceholderAsset(
        role="narration",
        filename="narration.wav",
        data=buffer.getvalue(),
        content_type="audio/wav",
    )


def generate_captions_vtt(scene: Scene) -> PlaceholderAsset:
    text = scene.narration.replace("\n", " ").strip()
    content = (
        "WEBVTT\n\n"
        f"1\n"
        f"00:00:00.000 --> 00:00:03.000\n"
        f"{text}\n"
    )
    return PlaceholderAsset(
        role="captions",
        filename="captions.vtt",
        data=content.encode("utf-8"),
        content_type="text/vtt",
    )


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def generate_clip_asset(scene: Scene, storyboard_png: bytes) -> PlaceholderAsset:
    if not ffmpeg_available():
        message = (
            f"Clip placeholder for {scene.scene_id}: ffmpeg not available.\n"
            "Install ffmpeg to generate a valid clip.mp4.\n"
        )
        return PlaceholderAsset(
            role="clip",
            filename="clip.placeholder.txt",
            data=message.encode("utf-8"),
            content_type="text/plain",
            playable=False,
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        storyboard_path = temp_path / "storyboard.png"
        clip_path = temp_path / "clip.mp4"
        storyboard_path.write_bytes(storyboard_png)

        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(storyboard_path),
            "-t",
            str(CLIP_DURATION_SECONDS),
            "-pix_fmt",
            "yuv420p",
            "-vf",
            f"scale={STORYBOARD_WIDTH}:{STORYBOARD_HEIGHT}",
            str(clip_path),
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                timeout=60,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            message = (
                f"Clip placeholder for {scene.scene_id}: ffmpeg failed.\n"
                "Check ffmpeg installation and retry.\n"
            )
            return PlaceholderAsset(
                role="clip",
                filename="clip.placeholder.txt",
                data=message.encode("utf-8"),
                content_type="text/plain",
                playable=False,
            )

        return PlaceholderAsset(
            role="clip",
            filename="clip.mp4",
            data=clip_path.read_bytes(),
            content_type="video/mp4",
        )


def generate_placeholder_assets(scene: Scene) -> list[PlaceholderAsset]:
    storyboard = generate_storyboard_png(scene)
    clip = generate_clip_asset(scene, storyboard.data)
    narration = generate_narration_wav(scene)
    captions = generate_captions_vtt(scene)
    return [storyboard, clip, narration, captions]
