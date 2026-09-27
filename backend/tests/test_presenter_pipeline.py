import pytest
import os
import tempfile
from app.services.script_service import determine_scene_mode
from app.providers.tts.voice_clone import LocalVoiceCloneProvider
from app.providers.presenter.local_presenter import LocalPresenterProvider

def test_scene_mode_determination():
    # Mode A (Presenter Video): All scenes should be PRESENTER
    for i in range(1, 6):
        assert determine_scene_mode(i, 5, mode="PRESENTER", has_presenter=True) == "PRESENTER"

    # Mode B (Content Video): Hybrid auto mode
    assert determine_scene_mode(1, 5, mode="CONTENT", frequency="automatic", has_presenter=True) == "PRESENTER" # Intro
    assert determine_scene_mode(2, 5, mode="CONTENT", frequency="automatic", has_presenter=True) == "MEDIA"     # Media
    assert determine_scene_mode(5, 5, mode="CONTENT", frequency="automatic", has_presenter=True) == "PRESENTER" # Outro

    # Without Presenter: All scenes default to MEDIA
    assert determine_scene_mode(1, 5, mode="CONTENT", frequency="automatic", has_presenter=False) == "MEDIA"

@pytest.mark.asyncio
async def test_voice_clone_missing_reference_raises_error():
    provider = LocalVoiceCloneProvider()
    with pytest.raises(ValueError, match="Presenter requires a voice reference"):
        await provider.generate_audio(
            text="Hello test",
            output_path="/tmp/test.wav",
            voice_reference_path="/nonexistent/path.wav"
        )

@pytest.mark.asyncio
async def test_local_presenter_missing_model_raises_error():
    provider = LocalPresenterProvider()
    provider.model_path = "/nonexistent/models/musetalk"
    
    with tempfile.NamedTemporaryFile(suffix=".mp4") as face_file, tempfile.NamedTemporaryFile(suffix=".wav") as audio_file:
        with pytest.raises(RuntimeError, match="(Local presenter model|MuseTalk inference failed)"):
            await provider.generate_presenter_clip(
                presenter_id="pres_123",
                face_reference_path=face_file.name,
                audio_path=audio_file.name,
                output_clip_path="/tmp/output_test.mp4"
            )
