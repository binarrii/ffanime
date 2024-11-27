import av
import os
import random
import subprocess
from typing import Callable, Dict, List, Tuple


def from_image(image: str, duration: int, size: Tuple[int, int] = (4096, 2304), fps: int = 25) -> str:
    filter = get_anime_filter(random.choice(list(_ANIME_FILTERS.keys())), duration * fps, size, fps)
    output = f"{os.path.dirname(image)}/{os.path.basename(image)}.mp4"
    subprocess.call(["ffmpeg", "-y", "-loop", "1", "-i", f"{image}", "-vf", f"{filter}", "-c:v", "libx264", "-r", f"{fps}", "-t", f"{duration}", output], cwd=os.path.dirname(output))
    return output

def add_audio(video: str, audio: str, output: str) -> str:
    subprocess.call(["ffmpeg", "-y", "-i", video, "-i", audio, "-c:v", "copy", "-c:a", "aac", "-strict", "experimental", output], cwd=os.path.dirname(output))
    return output

def add_subtitle(video: str, subtitle: str, output: str) -> str:
    subprocess.call(["ffmpeg", "-y", "-i", video, "-vf", f"subtitles={subtitle}", "-c:v", "copy", "-c:a", "copy", output], cwd=os.path.dirname(output))
    return output

def concat_videos(video_files: List[str], output: str) -> None:
    file_list = f"{os.path.dirname(output)}/file_list.txt"
    with open(file_list, "a+") as f:
        for video in video_files:
            f.write(f"file '{os.path.basename(video)}'\n")
    subprocess.call(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "file_list.txt", "-c", "copy", output], cwd=os.path.dirname(output))
    os.remove(file_list)

def concat_with_transition(video1: str, video2: str, output: str) -> None:
    temp_video1 = f"{os.path.dirname(output)}/temp_video1.mp4"
    temp_video2 = f"{os.path.dirname(output)}/temp_video2.mp4"
    
    fade_out_start = max(0, get_duration(video1) - 0.5)
    
    fade_out_filter = f"fade=t=out:st={fade_out_start}:d=0.5"
    subprocess.call(["ffmpeg", "-y", "-i", video1, "-vf", fade_out_filter, "-c:v", "libx264", temp_video1], cwd=os.path.dirname(temp_video1))
    
    fade_in_filter = f"fade=t=in:st=0:d=0.5"
    subprocess.call(["ffmpeg", "-y", "-i", video2, "-vf", fade_in_filter, "-c:v", "libx264", temp_video2], cwd=os.path.dirname(temp_video2))
    
    subprocess.call(["ffmpeg", "-y", "-i", temp_video1, "-i", temp_video2, "-filter_complex", "concat=n=2:v=1:a=0", "-c:v", "libx264", output], cwd=os.path.dirname(output))
    
    os.remove(temp_video1)
    os.remove(temp_video2)

def get_duration(video: str) -> float:
    with av.open(video) as container:
        duration = container.duration / av.time_base
    return duration

def get_anime_filter(anime: str, frames: int, size: Tuple[int, int], fps: int) -> str:
    filter_func = _ANIME_FILTERS.get(anime)
    return filter_func(frames, size, fps) if filter_func else ""

def fade_in(frames: int, size: Tuple[int, int], fps: int) -> str:
    return f"fade=in:st=0:d={frames}:s={size[0]}x{size[1]}:fps={fps}"

def fade_out(frames: int, size: Tuple[int, int], fps: int) -> str:
    return f"fade=out:st=0:d={frames}:s={size[0]}x{size[1]}:fps={fps}"

def zoom_in(frames: int, size: Tuple[int, int], fps: int) -> str:
    return f"scale=iw*2:-1,zoompan=z='zoom+0.001':x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):d={frames}:s={size[0]}x{size[1]}:fps={fps}"

def zoom_out(frames: int, size: Tuple[int, int], fps: int) -> str:
    return f"scale=iw*2:-1,zoompan=z='if(lte(zoom,1.0),1.25,max(1.001,zoom-0.001))':x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):d={frames}:s={size[0]}x{size[1]}:fps={fps}"

def slide_left(frames: int, size: Tuple[int, int], fps: int) -> str:
    return f"zoompan=z='1.25':x='if(lte(on,1),(iw-iw/zoom)/2,x+1)':y=0:d={frames}:s={size[0]}x{size[1]}:fps={fps}"

def slide_right(frames: int, size: Tuple[int, int], fps: int) -> str:
    return f"zoompan=z='1.25':x='if(lte(on,1),(iw-iw/zoom)/2,x-1)':y=0:d={frames}:s={size[0]}x{size[1]}:fps={fps}"

def slide_up(frames: int, size: Tuple[int, int], fps: int) -> str:
    return f"zoompan=z='1.25':x='if(lte(on,1),(iw-iw/zoom)/2,x)':y='if(lte(on,1),(ih-ih/zoom)/2,y+1):d={frames}:s={size[0]}x{size[1]}:fps={fps}"

def slide_down(frames: int, size: Tuple[int, int], fps: int) -> str:
    return f"zoompan=z='1.25':x='if(lte(on,1),(iw-iw/zoom)/2,x)':y='if(lte(on,1),(ih-ih/zoom)/2,y-1):d={frames}:s={size[0]}x{size[1]}:fps={fps}"

_ANIME_FILTERS: Dict[str, Callable[[int, Tuple[int, int], int], str]] = {
    "fade_in": fade_in,
    "fade_out": fade_out,
    "zoom_in": zoom_in,
    "zoom_out": zoom_out,
    "slide_left": slide_left,
    "slide_right": slide_right,
    "slide_up": slide_up,
    "slide_down": slide_down
}
