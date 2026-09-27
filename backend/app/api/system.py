import os
import shutil
import multiprocessing
from fastapi import APIRouter
from app.schemas.schemas import SystemCapabilitiesResponse

router = APIRouter(prefix="/system", tags=["System Capabilities"])

@router.get("/capabilities", response_model=SystemCapabilitiesResponse)
def get_system_capabilities():
    cpu_count = multiprocessing.cpu_count()
    cuda_avail = False
    mps_avail = False
    gpu_name = None
    gpu_mem = None

    try:
        import torch
        cuda_avail = torch.cuda.is_available()
        mps_avail = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
        if cuda_avail:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 1)
        elif mps_avail:
            gpu_name = "Apple Metal Performance Shaders (MPS)"
            gpu_mem = 16.0
    except ImportError:
        pass

    ff_path = shutil.which("ffmpeg")
    espeak_path = shutil.which("espeak")
    say_path = shutil.which("say")

    local_tts = bool(say_path or espeak_path or ff_path)
    
    # Check Voice Cloning Model Capability Status
    from app.providers.tts.voice_clone import LocalVoiceCloneProvider
    from app.providers.presenter.local_presenter import LocalPresenterProvider

    voice_clone_active = LocalVoiceCloneProvider.is_available()
    voice_clone_status = "READY" if voice_clone_active else "NOT_INSTALLED"

    presenter_prov = LocalPresenterProvider()
    pres_status_info = presenter_prov.get_engine_status()

    perf = "Excellent (Hardware GPU Accelerated)" if (cuda_avail or mps_avail) else "Good (Local CPU & Engine)"

    return SystemCapabilitiesResponse(
        cpu=True,
        cpu_count=cpu_count,
        gpu_available=(cuda_avail or mps_avail),
        gpu_name=gpu_name or ("Apple Silicon" if mps_avail else "CPU Only"),
        gpu_memory_gb=gpu_mem,
        mps_available=mps_avail,
        cuda_available=cuda_avail,
        local_llm_available=True,
        local_tts_available=local_tts,
        local_presenter_available=True,
        voice_clone_status=voice_clone_status,
        presenter_model_status=pres_status_info["status"],
        voice_engine=os.getenv("LOCAL_VOICE_ENGINE", "xtts_v2"),
        presenter_engine=os.getenv("LOCAL_PRESENTER_ENGINE", "musetalk"),
        estimated_performance=perf
    )

