from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

try:
    from vosk import KaldiRecognizer, Model
except Exception:
    KaldiRecognizer = None
    Model = None

VOICE_START_PHRASE = "jarvis start mission"
VOICE_END_PHRASE = "jarvis terminate mission"
VOICE_COMMANDS = (VOICE_START_PHRASE, VOICE_END_PHRASE)

NON_LETTER_RE = re.compile(r"[^a-z]+")


def normalize_transcript(text: str) -> str:
    lowered = text.strip().lower()
    replaced = NON_LETTER_RE.sub(" ", lowered)
    return " ".join(replaced.split())


@dataclass
class VoiceManager:
    model_path: Path | None
    sample_rate_hz: int = 16000

    def __post_init__(self) -> None:
        self._model = None
        self.available = False
        self.status_message = "Offline voice unavailable."

        if KaldiRecognizer is None or Model is None:
            self.status_message = "Install webapp Python dependencies to enable offline voice."
            return

        if not self.model_path or not self.model_path.exists():
            self.status_message = (
                "Vosk model not found. Run webapp/bootstrap.sh and place a model in webapp/models/."
            )
            return

        self._model = Model(str(self.model_path))
        self.available = True
        self.status_message = f"Offline voice ready from {self.model_path.name}."

    def create_session(self, threshold: float) -> "VoiceSession":
        if not self.available or self._model is None:
            raise RuntimeError(self.status_message)
        return VoiceSession(self._model, self.sample_rate_hz, threshold)


class VoiceSession:
    def __init__(self, model: Any, sample_rate_hz: int, threshold: float) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.threshold = max(0.0, min(1.0, float(threshold)))
        self._recognizer = KaldiRecognizer(model, float(sample_rate_hz), json.dumps(list(VOICE_COMMANDS)))
        self._recognizer.SetWords(True)
        self._last_partial = ""

    def feed_audio(self, pcm16_chunk: bytes) -> dict[str, Any] | None:
        if self._recognizer.AcceptWaveform(pcm16_chunk):
            result = json.loads(self._recognizer.Result() or "{}")
            text = result.get("text", "").strip()
            if text:
                self._last_partial = text
                return {"type": "voice_partial", "transcript": text}
            return None

        partial = json.loads(self._recognizer.PartialResult() or "{}").get("partial", "").strip()
        if partial and partial != self._last_partial:
            self._last_partial = partial
            return {"type": "voice_partial", "transcript": partial}
        return None

    def finalize(self) -> dict[str, Any]:
        result = json.loads(self._recognizer.FinalResult() or "{}")
        transcript = (result.get("text") or self._last_partial or "").strip()
        normalized = normalize_transcript(transcript)
        matched_command = normalized if normalized in VOICE_COMMANDS else None
        confidences = [float(item.get("conf", 0.0)) for item in result.get("result", []) if "conf" in item]
        if confidences:
            confidence = round(sum(confidences) / len(confidences), 3)
        else:
            confidence = 1.0 if matched_command else 0.0
        accepted = bool(matched_command) and confidence >= self.threshold
        return {
            "type": "voice_final",
            "transcript": transcript,
            "normalized_transcript": normalized,
            "confidence": confidence,
            "threshold": self.threshold,
            "matched_command": matched_command,
            "accepted": accepted,
        }