import math
import os
import shutil
import signal
import sys
import uuid
import uvicorn

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from utils import audio, video
from utils.storage import read_and_write


executor = ThreadPoolExecutor(max_workers=os.cpu_count() - 1)


class GenerateRequest(BaseModel):
    images: List[str]
    audios: Optional[List[str]] = None
    subtitles: Optional[List[str]] = None
    background_audio: Optional[str] = None
    opening: Optional[str] = None
    ending: Optional[str] = None
    cover: Optional[str] = None


app = FastAPI()

app.mount("/data", StaticFiles(directory="/data/ffanime"), name="static")


@app.post("/generate")
async def generate(request: GenerateRequest):
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
    
    date_str, uid = datetime.now().strftime("%Y%m%d"), uuid.uuid4()
    work_dir, output_dir = f"/tmp/{uid}", f"/data/ffanime/{date_str}"

    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    images = list(executor.map(lambda uri: read_and_write(uri, work_dir), request.images))
    audios = list(executor.map(lambda uri: read_and_write(uri, work_dir), request.audios)) if request.audios else None
    subtitles = list(executor.map(lambda uri: read_and_write(uri, work_dir), request.subtitles)) if request.subtitles else None
    background_audio = read_and_write(request.background_audio, work_dir) if request.background_audio else None
    opening = read_and_write(request.opening, work_dir) if request.opening else None
    ending = read_and_write(request.ending, work_dir) if request.ending else None
    cover = read_and_write(request.cover, work_dir) if request.cover else None

    if audios:
        durations = list(executor.map(audio.get_duration, audios))
        durations = [math.ceil(duration) for duration in durations]
    else:
        durations = [5] * len(images)

    videos = list(executor.map(video.from_image, images, durations))
    if audios:
        videos = list(executor.map(video.add_audio, videos, audios, [f"{work_dir}/output_aud_{os.path.basename(v)}" for v in videos]))
    if subtitles:
        videos = list(executor.map(video.add_subtitle, videos, subtitles, [f"{work_dir}/output_sub_{os.path.basename(v)}" for v in videos]))
    
    output_video = f"{work_dir}/{uid}.mp4"
    video.concat_all(videos, output_video)

    if background_audio:
        temp_output = f"{work_dir}/temp_output_with_bgaudio.mp4"
        video.add_audio(output_video, background_audio, temp_output, padding_mode="repeat")
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

    final_output_path = os.path.join(output_dir, os.path.basename(output_video))
    shutil.copy(output_video, final_output_path)
    shutil.rmtree(work_dir)

    return {"video": final_output_path}


if __name__ == "__main__":
    def _signal_handler(sig, frame):
        executor.shutdown(wait=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    uvicorn.run(app, host="0.0.0.0", port=8686)
