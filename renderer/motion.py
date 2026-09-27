import random

def get_ken_burns_filter(motion_type: str, width: int = 1920, height: int = 1080, duration: float = 6.0, fps: int = 30) -> str:
    """
    Generates FFmpeg zoompan filter string for smooth Ken Burns motion effects.
    Supports zoom_in, zoom_out, pan_left, pan_right, pan_up, pan_down.
    """
    total_frames = int(duration * fps)
    
    if motion_type == "zoom_in":
        # Zoom from 1.0 to 1.25 centered
        return f"zoompan=z='min(zoom+0.0015,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
    
    elif motion_type == "zoom_out":
        # Zoom out from 1.25 down to 1.0 centered
        return f"zoompan=z='if(lte(zoom,1.0),1.25,max(1.0,zoom-0.0015))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
    
    elif motion_type == "pan_left":
        # Pan across left to right at 1.15 zoom
        return f"zoompan=z='1.15':x='if(lte(on,1),(iw-iw/zoom),max(0,x-1.5))':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
    
    elif motion_type == "pan_right":
        # Pan right
        return f"zoompan=z='1.15':x='if(lte(on,1),0,min(iw-iw/zoom,x+1.5))':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
    
    elif motion_type == "pan_up":
        # Pan up
        return f"zoompan=z='1.15':x='iw/2-(iw/zoom/2)':y='if(lte(on,1),(ih-ih/zoom),max(0,y-1.5))':d={total_frames}:s={width}x{height}:fps={fps}"
    
    elif motion_type == "pan_down":
        # Pan down
        return f"zoompan=z='1.15':x='iw/2-(iw/zoom/2)':y='if(lte(on,1),0,min(ih-ih/zoom,y+1.5))':d={total_frames}:s={width}x{height}:fps={fps}"

    # Default random motion
    return f"zoompan=z='min(zoom+0.0012,1.20)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"

def get_random_motion_effect(scene_index: int) -> str:
    motions = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"]
    return motions[(scene_index - 1) % len(motions)]
