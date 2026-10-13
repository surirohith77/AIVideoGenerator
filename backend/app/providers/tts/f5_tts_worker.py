"""Persistent F5-TTS worker used to isolate its dependencies from Coqui XTTS."""

import contextlib
from concurrent.futures import Future
import json
import os
import secrets
import sys
import traceback
from typing import Any, Dict


class _SynchronousExecutor:
    """Run F5 inference chunks serially when using Apple MPS."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback_value):
        return False

    def submit(self, function, *args, **kwargs):
        future = Future()
        try:
            future.set_result(function(*args, **kwargs))
        except BaseException as error:
            future.set_exception(error)
        return future


def _write_response(response: Dict[str, Any]) -> None:
    sys.__stdout__.write(json.dumps(response) + "\n")
    sys.__stdout__.flush()


def main() -> int:
    try:
        with contextlib.redirect_stdout(sys.stderr):
            from f5_tts.api import F5TTS

            options: Dict[str, Any] = {"model": os.getenv("F5_TTS_MODEL", "F5TTS_v1_Base")}
            device = os.getenv("F5_TTS_DEVICE", "").strip()
            cache_dir = os.getenv("F5_TTS_CACHE_DIR", "").strip()
            if device:
                options["device"] = device
            if cache_dir:
                options["hf_cache_dir"] = cache_dir
            model = F5TTS(**options)
            if model.device == "mps":
                # F5's default ThreadPoolExecutor runs text chunks concurrently.
                # Concurrent inference calls can crash Apple's MPS command buffer.
                from f5_tts.infer import utils_infer

                utils_infer.ThreadPoolExecutor = _SynchronousExecutor
    except Exception as error:
        traceback.print_exc(file=sys.stderr)
        _write_response({"ready": False, "error": f"Could not initialize F5-TTS: {error}"})
        return 1

    _write_response({"ready": True})

    for line in sys.stdin:
        try:
            request = json.loads(line)
            with contextlib.redirect_stdout(sys.stderr):
                model.infer(
                    ref_file=request["reference_path"],
                    ref_text=request["reference_text"],
                    gen_text=request["text"],
                    file_wave=request["output_path"],
                    nfe_step=request["nfe_step"],
                    speed=request["speed"],
                    cfg_strength=request["cfg_strength"],
                    # F5-TTS writes its seed into PYTHONHASHSEED. Keep it in
                    # Python's supported 32-bit range so spawned workers start.
                    seed=secrets.randbelow(2**32),
                )
            _write_response({"ok": True})
        except Exception as error:
            traceback.print_exc(file=sys.stderr)
            _write_response({"ok": False, "error": f"F5-TTS inference failed: {error}"})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
