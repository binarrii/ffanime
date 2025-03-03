import shutil
import av
import os
import random
import subprocess
from typing import Callable, Dict, List, Optional, Tuple


def from_image(image: str, duration: int, size: Tuple[int, int] = (1920, 1080), fps: int = 25) -> str:
    duration = duration if duration > 0 else 5
    filter = get_anime_filter(random.choice(list(_ANIME_FILTERS.keys())), duration * fps, size, fps)
    output = f"{os.path.dirname(image)}/{os.path.basename(image)}.mp4"
    subprocess.call(["ffmpeg", "-y", "-loop", "1", "-i", f"{image}", "-vf", f"{filter}", "-c:v", "libx264", "-r", f"{fps}", "-t", f"{duration}", output], cwd=os.path.dirname(output))
    return output

def add_audio(video: str, audio: Optional[str], output: str, padding_mode: str = "silence") -> str:
    if audio is None:
        shutil.copy(video, output)
        return output
    if padding_mode == "silence":
        subprocess.call(["ffmpeg", "-y", "-i", video, "-i", audio, "-filter_complex", "[1:a]apad", \
            "-c:v", "copy", "-c:a", "aac", "-shortest", output], cwd=os.path.dirname(output))
    elif padding_mode == "repeat":
        subprocess.call(["ffmpeg", "-y", "-i", video, "-i", audio, "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=shortest,aloop=loop=-1,apad", \
            "-c:v", "copy", "-c:a", "aac", "-shortest", output], cwd=os.path.dirname(output))
    else:
        raise RuntimeError(f"Invalid padding mode: {padding_mode}")
    return output

def add_subtitle(video: str, subtitle: Optional[str], output: str) -> str:
    if subtitle is None:
        shutil.copy(video, output)
        return output
    subprocess.call(["ffmpeg", "-y", "-i", video, "-vf", f"subtitles={subtitle}", "-c", "copy", output], cwd=os.path.dirname(output))
    return output

def add_cover(video: str, image: str, output: str) -> str:
    subprocess.call(["ffmpeg", "-y", "-i", video, "-i", image, "-map", "1", "-map", "0", "-c", "copy", "-disposition:0", "attached_pic", output], cwd=os.path.dirname(output))
    return output

def concat_all(video_files: List[str], output: str) -> None:
    file_list = f"{os.path.dirname(output)}/file_list.txt"
    with open(file_list, "a+") as f:
        for video in video_files:
            f.write(f"file '{os.path.basename(video)}'\n")
    subprocess.call(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "file_list.txt", "-c", "copy", output], cwd=os.path.dirname(output))
    return output

def concat_with_transition(video1: str, video2: str, output: str, fps: int = 25) -> None:
    offset = max(0, get_duration(video1) - 0.5)
    subprocess.call(["ffmpeg", "-y", "-i", video1, "-i", video2, "-filter_complex", \
        f"[0:v]fps={fps},settb=AVTB,setpts=PTS-STARTPTS[v0];\
          [1:v]fps={fps},settb=AVTB,setpts=PTS-STARTPTS[v1];\
          [v0][v1]xfade=transition=fade:duration=1:offset={offset}[v];\
          [0:a]asettb=AVTB,asetpts=PTS-STARTPTS[a0];\
          [1:a]asettb=AVTB,asetpts=PTS-STARTPTS[a1];\
          [a0][a1]acrossfade=d=1:o=0[a]",
        "-movflags", "+faststart",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-c:a", "aac", output], cwd=os.path.dirname(output))
    return output

def get_duration(file_path: str) -> float:
    with av.open(file_path) as video:
        duration = video.duration / av.time_base
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
    # "fade_in": fade_in,
    # "fade_out": fade_out,
    "zoom_in": zoom_in,
    "zoom_out": zoom_out,
    "slide_left": slide_left,
    "slide_right": slide_right,
    "slide_up": slide_up,
    "slide_down": slide_down
}
