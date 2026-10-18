import os
import asyncio
import hashlib
import json
import logging
import shutil
import wave
from collections import deque
from pathlib import Path
from typing import Optional, Dict, Any
from app.providers.tts.base import TTSProvider
from app.providers.tts.f5_audio_postprocess import shorten_long_silences
from app.utils.media_verification import verify_output_media_file

logger = logging.getLogger(__name__)

_F5_TTS_ENGINES = {"f5", "f5_tts", "f5-tts"}
_XTTS_ENGINES = {"xtts", "xtts_v2", "xtts-v2"}
_F5_WORKER_PROCESS: Optional[asyncio.subprocess.Process] = None
_F5_WORKER_LOCK = asyncio.Lock()
_F5_WORKER_STDERR_TASK: Optional[asyncio.Task] = None
_F5_WORKER_STDERR_TAIL = deque(maxlen=30)
_DEFAULT_F5_REFERENCE_TEXT = (
    "Hi, thanks for taking a moment to listen. I'm going to talk about a few everyday things in my own words."
)


def _f5_python_executable() -> Optional[str]:
    configured = os.getenv("F5_TTS_PYTHON", "").strip()
    if configured:
        return configured if os.path.isfile(configured) else shutil.which(configured)

    backend_root = Path(__file__).resolve().parents[3]
    executable_name = "python.exe" if os.name == "nt" else "python"
    candidate = backend_root / "f5_venv" / ("Scripts" if os.name == "nt" else "bin") / executable_name
    return str(candidate) if candidate.is_file() else None


async def _log_f5_worker_stderr(process: asyncio.subprocess.Process) -> None:
    if not process.stderr:
        return
    while line := await process.stderr.readline():
        decoded_line = line.decode("utf-8", errors="replace").rstrip()
        _F5_WORKER_STDERR_TAIL.append(decoded_line)
        logger.info("F5-TTS worker: %s", decoded_line)


async def _ensure_f5_worker() -> asyncio.subprocess.Process:
    global _F5_WORKER_PROCESS, _F5_WORKER_STDERR_TASK

    if _F5_WORKER_PROCESS and _F5_WORKER_PROCESS.returncode is None:
        return _F5_WORKER_PROCESS

    python_executable = _f5_python_executable()
    if not python_executable:
        raise RuntimeError(
            "F5-TTS runtime is missing. Run backend/scripts/setup_f5_tts.sh or set F5_TTS_PYTHON."
        )

    worker_script = Path(__file__).with_name("f5_tts_worker.py")
    _F5_WORKER_STDERR_TAIL.clear()
    process = await asyncio.create_subprocess_exec(
        python_executable,
        str(worker_script),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _F5_WORKER_PROCESS = process
    _F5_WORKER_STDERR_TASK = asyncio.create_task(_log_f5_worker_stderr(process))

    startup_timeout = float(os.getenv("F5_TTS_STARTUP_TIMEOUT_SECONDS", "900"))
    try:
        ready_line = await asyncio.wait_for(process.stdout.readline(), timeout=startup_timeout)
        ready_response = json.loads(ready_line.decode("utf-8")) if ready_line else {}
    except Exception:
        process.kill()
        await process.wait()
        _F5_WORKER_PROCESS = None
        raise

    if not ready_response.get("ready"):
        process.kill()
        await process.wait()
        _F5_WORKER_PROCESS = None
        detail = ready_response.get("error", "The F5-TTS worker failed to initialize.")
        raise RuntimeError(detail)

    logger.info("F5-TTS worker is ready")
    return process


async def _run_f5_worker(request: Dict[str, Any], timeout: float) -> None:
    global _F5_WORKER_PROCESS

    async with _F5_WORKER_LOCK:
        process = await _ensure_f5_worker()
        if not process.stdin or not process.stdout:
            raise RuntimeError("F5-TTS worker pipes are unavailable.")

        process.stdin.write((json.dumps(request) + "\n").encode("utf-8"))
        await process.stdin.drain()
        try:
            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=timeout)
        except asyncio.TimeoutError as error:
            process.kill()
            await process.wait()
            _F5_WORKER_PROCESS = None
            raise RuntimeError(f"F5-TTS inference exceeded its {timeout:.0f}-second timeout.") from error

        if not response_line:
            await process.wait()
            if _F5_WORKER_STDERR_TASK:
                await _F5_WORKER_STDERR_TASK
            _F5_WORKER_PROCESS = None
            diagnostics = [
                line for line in _F5_WORKER_STDERR_TAIL
                if not line.lstrip().startswith(("ref_text", "gen_text"))
            ]
            diagnostic_tail = "\n".join(diagnostics[-8:])
            exit_status = f"exit code {process.returncode}"
            detail = f" Worker output: {diagnostic_tail}" if diagnostic_tail else ""
            raise RuntimeError(
                f"F5-TTS worker stopped before returning an audio result ({exit_status}).{detail}"
            )

        response = json.loads(response_line.decode("utf-8"))
        if not response.get("ok"):
            raise RuntimeError(response.get("error", "F5-TTS inference failed."))

class LocalVoiceCloneProvider(TTSProvider):
    """
    Local Voice Cloning Provider (Coqui XTTS-v2 Engine Adapter).
    Consumes voice_reference_path + new text script to synthesize speech in the user's reference voice.
    Strictly fails if voice reference or model is unavailable for Presenter mode.
    """
    def __init__(self):
        self.engine_name = os.getenv("LOCAL_VOICE_ENGINE", "f5_tts").lower()
        self.model_path = os.getenv("VOICE_MODEL_PATH", "")

    @staticmethod
    def is_available() -> bool:
        """
        Verifies if local voice cloning model runtime or checkpoints are available.
        """
        engine_name = os.getenv("LOCAL_VOICE_ENGINE", "f5_tts").lower()
        if engine_name in _F5_TTS_ENGINES:
            return bool(_f5_python_executable())

        if engine_name not in _XTTS_ENGINES:
            return False

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

        if self.engine_name in _F5_TTS_ENGINES:
            return await self._generate_f5_audio(text, output_path, speaker_reference_path)
        if self.engine_name not in _XTTS_ENGINES:
            raise RuntimeError(
                f"Unsupported LOCAL_VOICE_ENGINE '{self.engine_name}'. "
                "Choose f5_tts or xtts_v2."
            )

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

    async def _generate_f5_audio(self, text: str, output_path: str, reference_path: str) -> str:
        request = {
            "reference_path": reference_path,
            "reference_text": os.getenv("F5_TTS_REFERENCE_TEXT", _DEFAULT_F5_REFERENCE_TEXT).strip(),
            "text": text,
            "output_path": output_path,
            "nfe_step": int(os.getenv("F5_TTS_NFE_STEP", "32")),
            "speed": float(os.getenv("F5_TTS_SPEED", "1.2")),
            "cfg_strength": float(os.getenv("F5_TTS_CFG_STRENGTH", "2.0")),
        }
        timeout = float(os.getenv("F5_TTS_TIMEOUT_SECONDS", "900"))
        await _run_f5_worker(request, timeout=timeout)

        if not os.path.isfile(output_path) or os.path.getsize(output_path) <= 1024:
            raise RuntimeError("F5-TTS completed without producing a valid audio file.")

        removed_pause_seconds = shorten_long_silences(output_path)
        if removed_pause_seconds:
            logger.info(
                "F5-TTS shortened long pauses by %.2f seconds (minimum=%ss, retained=%ss)",
                removed_pause_seconds,
                os.getenv("F5_TTS_PAUSE_MIN_SECONDS", "0.60"),
                os.getenv("F5_TTS_PAUSE_RETAIN_SECONDS", "0.32"),
            )

        verification = await verify_output_media_file(output_path, require_audio=True)
        logger.info(
            "F5-TTS audio verified: size=%sB, duration=%ss",
            verification["size"],
            verification["duration"],
        )
        return output_path
