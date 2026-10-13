import os
import asyncio
import hashlib
import logging
import wave
from typing import Optional, Dict, Any
from app.providers.tts.base import TTSProvider
from app.utils.media_verification import verify_output_media_file

logger = logging.getLogger(__name__)

class LocalVoiceCloneProvider(TTSProvider):
    """
    Local Voice Cloning Provider (Coqui XTTS-v2 Engine Adapter).
    Consumes voice_reference_path + new text script to synthesize speech in the user's reference voice.
    Strictly fails if voice reference or model is unavailable for Presenter mode.
    """
    def __init__(self):
        self.engine_name = os.getenv("LOCAL_VOICE_ENGINE", "xtts_v2").lower()
        self.model_path = os.getenv("VOICE_MODEL_PATH", "")

    @staticmethod
    def is_available() -> bool:
        """
        Verifies if local voice cloning model runtime or checkpoints are available.
        """
        model_dir = os.getenv("VOICE_MODEL_PATH", "")
        if model_dir and os.path.exists(model_dir):
            return True
        import shutil
        if shutil.which("tts"):
            return True
        try:
            import TTS  # noqa: F401
            return True
        except ImportError:
            return False

    async def _prepare_voice_reference(self, voice_reference_path: str) -> str:
        """Normalize uploaded media to the PCM WAV format XTTS expects.

        Some browser recordings arrive as WebM/Opus even when named `.wav`.
        The content-hash cache handles existing assets without modifying the
        user's original recording.
        """
        digest = hashlib.sha256()
        with open(voice_reference_path, "rb") as source:
            for chunk in iter(lambda: source.read(65536), b""):
                digest.update(chunk)

        cache_dir = os.path.join(os.path.dirname(voice_reference_path), ".xtts_reference_cache")
        os.makedirs(cache_dir, exist_ok=True)
        prepared_path = os.path.join(cache_dir, f"{digest.hexdigest()}.wav")
        if os.path.exists(prepared_path) and os.path.getsize(prepared_path) > 1024:
            return prepared_path

        cmd = [
            "ffmpeg", "-y", "-v", "error", "-i", voice_reference_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
            prepared_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0 or not os.path.exists(prepared_path) or os.path.getsize(prepared_path) <= 1024:
            detail = stderr.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(f"Could not prepare XTTS voice reference as PCM WAV: {detail}")
        return prepared_path

    @staticmethod
    def _reference_conditioning_options(reference_path: str) -> Dict[str, int]:
        """Use one XTTS style chunk for short references to retain voice traits."""
        try:
            with wave.open(reference_path, "rb") as reference:
                duration = reference.getnframes() / float(reference.getframerate())
        except (OSError, wave.Error, ZeroDivisionError):
            logger.warning("Could not read voice reference duration; using XTTS defaults")
            return {}

        conditioning_length = min(30, max(1, int(duration)))
        if conditioning_length <= 10:
            return {
                "gpt_cond_len": conditioning_length,
                "gpt_cond_chunk_len": conditioning_length,
            }
        return {"gpt_cond_len": conditioning_length, "gpt_cond_chunk_len": 4}

    async def generate_audio(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        voice_reference_path: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if not voice_reference_path or not os.path.exists(voice_reference_path):
            raise ValueError(
                "ERROR: Presenter requires a voice reference. "
                "No voice_reference_path provided or file missing. "
                "Please record or upload a voice reference audio file."
            )

        speaker_reference_path = await self._prepare_voice_reference(voice_reference_path)

        # Set TOS agreement automatically to avoid hanging stdout/stdin prompts
        os.environ["COQUI_TOS_AGREED"] = "1"

        logger.info(
            f"\n========== AI VOICE CLONING ==========\n"
            f"Voice engine: {self.engine_name}\n"
            f"Voice reference: {voice_reference_path}\n"
            f"XTTS PCM reference: {speaker_reference_path}\n"
            f"Output path: {output_path}\n"
            f"Script text: {text[:60]}...\n"
            f"======================================="
        )

        # Method 1: PyTorch TTS Python API (In-memory execution)
        try:
            import torch
            import torchaudio
            import soundfile as sf

            # Monkeypatch PyTorch 2.6+ weights_only=True default for Coqui TTS checkpoints
            if not getattr(torch, "_xtts_patched", False):
                _orig_torch_load = torch.load
                def _patched_torch_load(*args, **kwargs):
                    if "weights_only" not in kwargs:
                        kwargs["weights_only"] = False
                    return _orig_torch_load(*args, **kwargs)
                torch.load = _patched_torch_load

                # Patch torchaudio.load with soundfile to avoid torchcodec requirement
                _orig_ta_load = torchaudio.load
                def _patched_ta_load(uri, frame_offset=0, num_frames=-1, normalize=True, channels_first=True, **kwargs):
                    try:
                        data, sample_rate = sf.read(
                            uri,
                            start=frame_offset,
                            stop=(frame_offset + num_frames) if num_frames > 0 else None,
                            dtype='float32'
                        )
                        tensor = torch.from_numpy(data)
                        if tensor.ndim == 1:
                            tensor = tensor.unsqueeze(1)
                        if channels_first:
                            tensor = tensor.t()
                        return tensor, sample_rate
                    except Exception:
                        return _orig_ta_load(uri, frame_offset=frame_offset, num_frames=num_frames, normalize=normalize, channels_first=channels_first)

                torchaudio.load = _patched_ta_load
                torch._xtts_patched = True

            import gc
            import resource
            rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
            print(f"[Memory] Before XTTS: RSS={rss_mb:.2f} MB")

            from TTS.api import TTS
            device = "cuda" if torch.cuda.is_available() else ("mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu")
            logger.info(f"Loaded Coqui TTS API on device={device}")
            
            def run_tts_inference():
                tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2").to(device)
                conditioning_options = self._reference_conditioning_options(speaker_reference_path)
                tts.tts_to_file(
                    text=text,
                    speaker_wav=speaker_reference_path,
                    language="en",
                    file_path=output_path,
                    **conditioning_options,
                )
                del tts
            
            # 5 minute timeout for TTS inference to prevent infinite hanging
            await asyncio.wait_for(asyncio.to_thread(run_tts_inference), timeout=300.0)

            print("[XTTS] Generation complete")
            print("[XTTS] Releasing memory before MuseTalk")
            gc.collect()
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                torch.mps.empty_cache()

            rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
            print(f"[Memory] After XTTS: RSS={rss_after:.2f} MB")

            if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                verification = await verify_output_media_file(output_path, require_audio=True)
                logger.info(f"[Voice Cloning Success] Output WAV verified: size={verification['size']}B, duration={verification['duration']}s")
                return output_path
        except Exception as e:
            logger.warning(f"Python TTS API inference attempt failed/skipped: {e}. Trying CLI / model script...")

        # Method 2: CLI Binary invocation
        import shutil
        tts_cli = shutil.which("tts")
        if tts_cli:
            cmd = [
                tts_cli,
                "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
                "--text", text,
                "--speaker_wav", speaker_reference_path,
                "--language_idx", "en",
                "--out_path", output_path
            ]
            logger.info(f"Executing CLI voice cloning command: {' '.join(cmd)}")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300.0)
                if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                    verification = await verify_output_media_file(output_path, require_audio=True)
                    logger.info(f"[Voice Cloning CLI Success] Output WAV verified: size={verification['size']}B, duration={verification['duration']}s")
                    return output_path
                else:
                    logger.error(f"XTTS CLI inference failed: {stderr.decode('utf-8', errors='ignore')}")
            except asyncio.TimeoutError:
                proc.kill()
                raise RuntimeError("XTTS CLI inference timed out after 300 seconds.")

        # Method 3: Custom script inside model_path
        if self.model_path and os.path.exists(self.model_path):
            script_path = os.path.join(self.model_path, "clone_voice.py")
            if os.path.exists(script_path):
                cmd = [
                    "python3", script_path,
                    "--text", text,
                    "--reference_wav", speaker_reference_path,
                    "--output", output_path
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                try:
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300.0)
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                        verification = await verify_output_media_file(output_path, require_audio=True)
                        return output_path
                except asyncio.TimeoutError:
                    proc.kill()
                    raise RuntimeError("Custom voice cloning script timed out after 300 seconds.")

        # Fail explicitly for Presenter mode - DO NOT fall back to macOS say
        raise RuntimeError(
            f"Voice cloning model ({self.engine_name}) is not installed or failed to execute. "
            f"Presenter voice cloning requires XTTS-v2 runtime or model weights at '{self.model_path}'."
        )
