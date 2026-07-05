"""Genblaze provider selection — GMI Cloud preferred, OpenAI fallback.

Builds an ordered attempt chain per generation step. Callers try providers
in order and record which one actually ran; nothing here fakes usage.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Live-verified defaults (see docs/genblaze-pipeline.md):
# - DeepSeek-V3.2 on GMI honors strict json_schema structured output.
# - Image/TTS slugs are pattern pass-through in the GMI registry; a wrong
#   slug fails cleanly into the OpenAI fallback.
_GMI_DEFAULTS = {
    "chat": "deepseek-ai/DeepSeek-V3.2",
    "image": "seedream-4-0-250828",
    # elevenlabs-tts-v3 appears in the queue catalog but probes DEAD on the
    # hackathon account; MiniMax TTS is live-verified.
    "tts": "minimax-tts-speech-2.6-turbo",
}


@dataclass(frozen=True)
class ProviderChoice:
    name: str  # "gmi" | "openai"
    model: str


def _gmi_configured() -> bool:
    if not os.getenv("GMI_API_KEY", "").strip():
        return False
    try:
        import genblaze_gmicloud  # noqa: F401
    except ImportError:
        return False
    return True


def _openai_configured() -> bool:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return False
    try:
        import genblaze_openai  # noqa: F401
    except ImportError:
        return False
    return True


def _model_for(provider: str, step: str) -> str:
    if provider == "gmi":
        return os.getenv(
            f"SCENELEDGER_GMI_{step.upper()}_MODEL", _GMI_DEFAULTS[step]
        ).strip()
    openai_defaults = {
        "chat": "gpt-4o-mini",
        "image": "gpt-image-1",
        "tts": "gpt-4o-mini-tts",
    }
    env_names = {
        "chat": "SCENELEDGER_GENBLAZE_CHAT_MODEL",
        "image": "SCENELEDGER_GENBLAZE_IMAGE_MODEL",
        "tts": "SCENELEDGER_GENBLAZE_TTS_MODEL",
    }
    return os.getenv(env_names[step], openai_defaults[step]).strip()


def gmi_tts_voice() -> str:
    """GMI TTS voice id; empty string means use the model's default voice."""
    return os.getenv("SCENELEDGER_GMI_TTS_VOICE", "").strip()


def openai_tts_voice() -> str:
    return os.getenv("SCENELEDGER_GENBLAZE_TTS_VOICE", "alloy").strip()


def preferred_provider() -> str:
    return os.getenv("SCENELEDGER_GENBLAZE_PROVIDER", "openai").strip().lower()


def provider_chain(step: str) -> list[ProviderChoice]:
    """Ordered provider attempts for a step ("chat" | "image" | "tts").

    Preferred provider first (when configured), then the fallback provider
    (when configured and different). Empty when neither is configured —
    callers surface a clear configuration error or fall back honestly.
    """
    preferred = preferred_provider()
    fallback = (
        os.getenv("SCENELEDGER_GENBLAZE_FALLBACK_PROVIDER", "openai")
        .strip()
        .lower()
    )
    configured = {"gmi": _gmi_configured(), "openai": _openai_configured()}

    chain: list[ProviderChoice] = []
    for name in [preferred, fallback]:
        if name in configured and configured[name] and all(
            c.name != name for c in chain
        ):
            chain.append(ProviderChoice(name=name, model=_model_for(name, step)))
    return chain
