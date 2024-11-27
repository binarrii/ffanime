import math
import os
import shutil
import signal
import sys
import uuid
import uvicorn

from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
from fastapi import FastAPI
from utils import audio, video
from utils.storage import read_and_write

_OUTPUT_DIR = "/data/ffanime_output"

executor = ThreadPoolExecutor(max_workers=os.cpu_count() - 1)

app = FastAPI()

@app.post("/generate")
def generate(
    images: List[str],
    audios: Optional[List[str]] = None,
    subtitles: Optional[List[str]] = None,
    background_sound: Optional[str] = None,
    opening: Optional[str] = None,
    ending: Optional[str] = None,
    cover: Optional[str] = None,
):
    """
    Generate a video from images, with optional audio, subtitles, background sound, opening, and ending.

    Args:
        images (List[str]): List of image URIs.
        audios (Optional[List[str]]): List of audio URIs.
        subtitles (Optional[List[str]]): List of subtitle URIs.
        background_sound (Optional[str]): URI of the background sound.
        opening (Optional[str]): URI of the opening video.
        ending (Optional[str]): URI of the ending video.

    Returns:
        dict: A dictionary containing the path to the generated video.

    Example:
        {
            "images": ["file:///path/to/image1.jpg", "file:///path/to/image2.jpg"],
            "audios": ["file:///path/to/audio1.mp3", "file:///path/to/audio2.mp3"],
            "subtitles": ["file:///path/to/subtitle1.srt", "file:///path/to/subtitle2.srt"],
            "background_sound": "file:///path/to/background.mp3",
            "opening": "file:///path/to/opening.mp4",
            "ending": "file:///path/to/ending.mp4"
        }
    """
    work_dir = f"/tmp/{uuid.uuid5(uuid.NAMESPACE_DNS, str(uuid.uuid1()))}"
    os.makedirs(work_dir, exist_ok=True)

    images = list(executor.map(lambda uri: read_and_write(uri, work_dir), images))
    if audios:
        audios = list(executor.map(lambda uri: read_and_write(uri, work_dir), audios))
    if subtitles:
        subtitles = list(executor.map(lambda uri: read_and_write(uri, work_dir), subtitles))
    if background_sound:
        background_sound = read_and_write(background_sound, work_dir)
    if opening:
        opening = read_and_write(opening, work_dir)
    if ending:
        ending = read_and_write(ending, work_dir)

    if audios:
        durations = list(executor.map(audio.get_duration, audios))
        durations = [math.ceil(duration) for duration in durations]
    else:
        durations = [5] * len(images)

    videos = list(executor.map(video.from_image, images, durations))
    if audios:
        videos = list(executor.map(video.add_audio, videos, audios, [f"{work_dir}/output_{os.path.basename(v)}" for v in videos]))
    if subtitles:
        videos = list(executor.map(video.add_subtitle, videos, subtitles, [f"{work_dir}/output_sub_{os.path.basename(v)}" for v in videos]))
    
    output_video = f"{work_dir}/final_output.mp4"
    video.concat_all(videos, output_video)

    if background_sound:
        temp_output = f"{work_dir}/temp_output_with_audio.mp4"
        video.add_audio(output_video, background_sound, temp_output)
        os.rename(temp_output, output_video)

    if opening:
        temp_output = f"{work_dir}/temp_output_with_opening.mp4"
        video.concat_with_transition(opening, output_video, temp_output)
        os.rename(temp_output, output_video)

    if ending:
        temp_output = f"{work_dir}/temp_output_with_ending.mp4"
        video.concat_with_transition(output_video, ending, temp_output)
        os.rename(temp_output, output_video)

    if cover:
        temp_output = f"{work_dir}/temp_output_with_cover.mp4"
        video.add_cover(output_video, cover, temp_output)
        os.rename(temp_output, output_video)

    final_output_path = os.path.join(_OUTPUT_DIR, os.path.basename(output_video))
    shutil.copy(output_video, final_output_path)
    # shutil.rmtree(work_dir)

    return {"video": final_output_path}


if __name__ == "__main__":
    os.makedirs(_OUTPUT_DIR, exist_ok=True)

    def _signal_handler(sig, frame):
        executor.shutdown(wait=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    uvicorn.run(app, host="0.0.0.0", port=8686)
