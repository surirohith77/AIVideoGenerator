import os
import asyncio
import logging
import tempfile
import functools
import subprocess
from typing import List, Dict, Any, Optional
from renderer.motion import get_ken_burns_filter, get_random_motion_effect

logger = logging.getLogger(__name__)

@functools.lru_cache(maxsize=32)
def has_ffmpeg_filter(filter_name: str) -> bool:
    try:
        res = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True)
        return filter_name in res.stdout
    except Exception:
        return False

def parse_aspect_ratio(aspect_ratio: str, resolution: str) -> tuple[int, int]:
    is_720p = "720" in resolution
    if aspect_ratio == "9:16":
        return (720, 1280) if is_720p else (1080, 1920)
    elif aspect_ratio == "1:1":
        return (720, 720) if is_720p else (1080, 1080)
    else: # 16:9
        return (1280, 720) if is_720p else (1920, 1080)

def generate_srt_file(scenes: List[Dict[str, Any]], output_srt_path: str):
    current_time = 0.0
    srt_entries = []
    
    for idx, scene in enumerate(scenes, 1):
        dur = float(scene.get("duration", 6.0))
        caption = scene.get("caption") or scene.get("narration") or ""
        if not caption:
            current_time += dur
            continue
            
        start_sec = current_time
        end_sec = current_time + dur
        current_time = end_sec

        def format_timestamp(seconds: float) -> str:
            millis = int((seconds % 1) * 1000)
            total_sec = int(seconds)
            secs = total_sec % 60
            mins = (total_sec // 60) % 60
            hrs = total_sec // 3600
            return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

        srt_entries.append(f"{idx}\n{format_timestamp(start_sec)} --> {format_timestamp(end_sec)}\n{caption}\n")

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_entries))

class FFmpegRenderer:
    def __init__(self, storage_path: str = "./storage"):
        self.storage_path = storage_path

    async def render_scene_clip(
        self,
        scene: Dict[str, Any],
        scene_index: int,
        width: int,
        height: int,
        output_clip_path: str
    ) -> str:
        os.makedirs(os.path.dirname(output_clip_path), exist_ok=True)
        asset_path = scene.get("asset_path")
        visual_type = scene.get("visual_type", "IMAGE")
        duration = float(scene.get("duration", 6.0))
        frame_count = int(scene.get("_frame_count", round(duration * 30)))
        render_duration = frame_count / 30.0

        if not asset_path or not os.path.exists(asset_path):
            cmd = [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"color=c=0x0f172a:s={width}x{height}:d={render_duration}",
                "-frames:v", str(frame_count), "-an",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", output_clip_path
            ]
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.communicate()
            return output_clip_path

        if visual_type == "IMAGE":
            motion_type = scene.get("motion_type") or get_random_motion_effect(scene_index)
            kb_filter = get_ken_burns_filter(motion_type, width=width, height=height, duration=render_duration, fps=30)
            filtergraph = f"scale=-2:{height}*2,crop=iw:ih,format=yuv420p,{kb_filter}"
            
            cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", asset_path,
                "-vf", filtergraph,
                "-frames:v", str(frame_count), "-an",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                output_clip_path
            ]
        else:
            filtergraph = (
                f"setpts=PTS-STARTPTS,fps=30:start_time=0,"
                f"tpad=stop_mode=clone:stop_duration={render_duration},"
                f"trim=end_frame={frame_count},setpts=PTS-STARTPTS,"
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},format=yuv420p"
            )
            cmd = [
                "ffmpeg", "-y", "-i", asset_path,
                "-vf", filtergraph,
                "-frames:v", str(frame_count), "-an",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                output_clip_path
            ]

        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        return output_clip_path

    async def render_full_project_video(
        self,
        project_name: str,
        style_profile: Dict[str, Any],
        scenes: List[Dict[str, Any]],
        output_mp4_path: str,
        progress_callback = None
    ) -> str:
        os.makedirs(os.path.dirname(output_mp4_path), exist_ok=True)
        width, height = parse_aspect_ratio(
            style_profile.get("aspect_ratio", "16:9"),
            style_profile.get("resolution", "1080p")
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            clip_paths = []
            audio_paths = []
            render_scenes = []
            cumulative_duration = 0.0
            previous_frame_end = 0
            for scene in scenes:
                render_scene = dict(scene)
                cumulative_duration += float(scene.get("duration", 6.0))
                frame_end = round(cumulative_duration * 30)
                render_scene["_frame_count"] = frame_end - previous_frame_end
                previous_frame_end = frame_end
                render_scenes.append(render_scene)

            # Step 1: Render individual scene clips
            for idx, scene in enumerate(render_scenes, 1):
                if progress_callback:
                    await progress_callback(stage="CREATING_SCENES", progress=int(20 + (idx / len(scenes)) * 40))
                
                clip_file = os.path.join(temp_dir, f"scene_{idx:03d}.mp4")
                await self.render_scene_clip(scene, idx, width, height, clip_file)
                clip_paths.append(clip_file)

                audio_path = scene.get("audio_path")
                audio_paths.append(audio_path if audio_path and os.path.exists(audio_path) else None)

            # Step 2: Concatenate scene clips
            concat_list_file = os.path.join(temp_dir, "clips.txt")
            with open(concat_list_file, "w") as f:
                for cp in clip_paths:
                    f.write(f"file '{cp}'\n")

            merged_visual_path = os.path.join(temp_dir, "merged_visuals.mp4")
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list_file,
                "-c", "copy", merged_visual_path
            ]
            proc = await asyncio.create_subprocess_exec(*concat_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.communicate()

            # Step 3: Concatenate narration audio
            merged_narration_path = None
            if any(audio_paths):
                # Keep the audio timeline in lockstep with the scene clips. A scene
                # without narration still occupies time in the video, so represent
                # it with silence instead of removing it from the audio concat.
                for idx, (scene, audio_path) in enumerate(zip(render_scenes, audio_paths)):
                    if audio_path is not None:
                        continue

                    duration = max(float(scene.get("duration", 6.0)), 0.001)
                    silence_path = os.path.join(temp_dir, f"silence_{idx + 1:03d}.wav")
                    silence_cmd = [
                        "ffmpeg", "-y", "-f", "lavfi",
                        "-i", "anullsrc=r=44100:cl=stereo",
                        "-t", f"{duration:.6f}",
                        "-c:a", "pcm_s16le", silence_path
                    ]
                    proc = await asyncio.create_subprocess_exec(
                        *silence_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    _, stderr = await proc.communicate()
                    if proc.returncode != 0:
                        raise RuntimeError(
                            f"Failed to create silent audio for scene {idx + 1}: "
                            f"{stderr.decode('utf-8', errors='ignore')[-500:]}"
                        )
                    audio_paths[idx] = silence_path

                audio_concat_file = os.path.join(temp_dir, "audio.txt")
                with open(audio_concat_file, "w") as f:
                    for ap in audio_paths:
                        f.write(f"file '{ap}'\n")
                
                merged_narration_path = os.path.join(temp_dir, "merged_narration.wav")
                ac_cmd = [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", audio_concat_file,
                    "-c", "pcm_s16le", merged_narration_path
                ]
                proc = await asyncio.create_subprocess_exec(*ac_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                await proc.communicate()

            if progress_callback:
                await progress_callback(stage="RENDERING", progress=75)

            # Step 4: Final FFmpeg Assembly
            ffmpeg_inputs = ["-i", merged_visual_path]
            filter_complex_parts = ["[0:v]setpts=PTS-STARTPTS[vbase]"]
            input_idx = 1

            if merged_narration_path and os.path.exists(merged_narration_path):
                ffmpeg_inputs.extend(["-i", merged_narration_path])
                narration_idx = input_idx
                input_idx += 1
            else:
                narration_idx = None

            music_path = style_profile.get("music_path")
            music_vol = style_profile.get("music_volume", 0.12)
            if music_path and os.path.exists(music_path):
                ffmpeg_inputs.extend(["-i", music_path])
                music_idx = input_idx
                input_idx += 1
            else:
                music_idx = None

            logo_path = style_profile.get("logo_path")
            use_logo = style_profile.get("use_logo", True)
            if logo_path and use_logo and os.path.exists(logo_path):
                ffmpeg_inputs.extend(["-i", logo_path])
                logo_idx = input_idx
                input_idx += 1
            else:
                logo_idx = None

            video_stream = "vbase"
            
            # Caption overlay (subtitles -> drawtext -> fallback)
            scene_captions = [s.get("caption") or s.get("narration") for s in render_scenes if s.get("caption") or s.get("narration")]
            if scene_captions:
                if has_ffmpeg_filter("subtitles"):
                    srt_path = os.path.join(temp_dir, "subtitles.srt")
                    generate_srt_file(render_scenes, srt_path)
                    clean_srt_path = srt_path.replace(":", "\\:").replace("'", "\\'")
                    filter_complex_parts.append(f"[{video_stream}]subtitles=filename='{clean_srt_path}':force_style='FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3'[vsub]")
                    video_stream = "vsub"
                elif has_ffmpeg_filter("drawtext"):
                    caption_str = scene_captions[0].replace("'", "").replace(":", "")[:50]
                    filter_complex_parts.append(
                        f"[{video_stream}]drawtext=text='{caption_str}':x=(w-text_w)/2:y=h-60:"
                        f"fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=8[vsub]"
                    )
                    video_stream = "vsub"

            # Logo overlay
            if logo_idx is not None:
                filter_complex_parts.append(f"[{logo_idx}:v]scale=120:-1[scaled_logo]")
                filter_complex_parts.append(f"[{video_stream}][scaled_logo]overlay=main_w-overlay_w-30:30[vlogo]")
                video_stream = "vlogo"

            # Audio mixing
            audio_stream = None
            if narration_idx is not None and music_idx is not None:
                filter_complex_parts.append(f"[{music_idx}:a]volume={music_vol}[bgm]")
                filter_complex_parts.append(f"[{narration_idx}:a][bgm]amix=inputs=2:duration=first[aout]")
                audio_stream = "aout"
            elif narration_idx is not None:
                audio_stream = f"{narration_idx}:a"
            elif music_idx is not None:
                filter_complex_parts.append(f"[{music_idx}:a]volume={music_vol}[bgm]")
                audio_stream = "bgm"

            final_cmd = ["ffmpeg", "-y"] + ffmpeg_inputs
            
            if filter_complex_parts:
                final_cmd.extend(["-filter_complex", ";".join(filter_complex_parts)])

            final_cmd.extend(["-map", f"[{video_stream}]" if filter_complex_parts else "0:v"])
            
            if audio_stream:
                if "[" in audio_stream:
                    final_cmd.extend(["-map", f"[{audio_stream}]"])
                else:
                    final_cmd.extend(["-map", audio_stream])
                final_cmd.extend(["-c:a", "aac", "-b:a", "192k"])
            else:
                total_duration = sum(float(s.get("duration", 6.0)) for s in render_scenes)
                final_cmd.extend(["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo", "-t", str(total_duration), "-c:a", "aac"])

            final_cmd.extend([
                "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p",
                output_mp4_path
            ])

            proc = await asyncio.create_subprocess_exec(*final_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"FFmpeg final assembly failed: {stderr.decode('utf-8')}")
                raise RuntimeError(f"FFmpeg rendering failed: {stderr.decode('utf-8')[-500:]}")

            if progress_callback:
                await progress_callback(stage="COMPLETED", progress=100)

            return output_mp4_path
