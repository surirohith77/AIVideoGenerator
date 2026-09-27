import os
import tempfile
import pytest
import asyncio
from renderer.ffmpeg_builder import FFmpegRenderer

@pytest.mark.asyncio
async def test_ffmpeg_rendering_pipeline():
    renderer = FFmpegRenderer()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create synthetic test image
        img_path = os.path.join(tmp_dir, "test.png")
        cmd_img = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "color=c=0x0284c7:s=1920x1080:d=1",
            "-frames:v", "1", img_path
        ]
        proc = await asyncio.create_subprocess_exec(*cmd_img, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        assert os.path.exists(img_path)

        # Create synthetic test audio
        aud_path = os.path.join(tmp_dir, "test.wav")
        cmd_aud = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo", "-t", "4.0", aud_path
        ]
        proc = await asyncio.create_subprocess_exec(*cmd_aud, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        assert os.path.exists(aud_path)

        # Render complete project video
        output_mp4 = os.path.join(tmp_dir, "output.mp4")
        scenes = [
            {
                "scene_number": 1,
                "narration": "India and Russia have maintained a long relationship.",
                "duration": 4.0,
                "visual_type": "IMAGE",
                "asset_path": img_path,
                "audio_path": aud_path,
                "caption": "India and Russia Relationship"
            }
        ]
        style = {
            "aspect_ratio": "16:9",
            "resolution": "1080p",
            "music_volume": 0.12,
            "use_logo": False
        }

        rendered_file = await renderer.render_full_project_video("Test Project", style, scenes, output_mp4)
        assert os.path.exists(rendered_file)
        assert os.path.getsize(rendered_file) > 1000
