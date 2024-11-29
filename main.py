import dotenv
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
from typing import List, Literal, Optional
from utils import audio, video
from utils.storage import read_and_write

dotenv.load_dotenv(dotenv_path=f"{os.path.dirname(__file__)}/.env")

_OUTPUT_DIR = os.getenv("FFANIME_OUTPUT_DIR", "/data/ffanime").rstrip("/")
_HTTP_PREFIX = os.getenv("FFANIME_HTTP_PREFIX", "http://localhost:8686").rstrip("/")
_PATH_PREFIX = os.getenv("FFANIME_PATH_PREFIX", f"{_OUTPUT_DIR}").rstrip("/")
os.makedirs(_OUTPUT_DIR, exist_ok=True)


executor = ThreadPoolExecutor(max_workers=max(1, os.cpu_count() - 1))


class GenerateRequest(BaseModel):
    images: List[str]
    audios: Optional[List[str | None]] = None
    subtitles: Optional[List[str | None]] = None
    background_audio: Optional[str] = None
    opening: Optional[str] = None
    ending: Optional[str] = None
    cover: Optional[str] = None
    response_type: Literal["url", "path"] = "url"


app = FastAPI()

app.mount("/data", StaticFiles(directory=f"{_OUTPUT_DIR}"), name="static")


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
            "response_type": "url",
            "images": [
                "http://192.168.1.73/resources/ffanime/1000.jpg",
                "http://192.168.1.73/resources/ffanime/1001.jpg",
                "http://192.168.1.73/resources/ffanime/1002.jpg",
                "http://192.168.1.73/resources/ffanime/1003.jpg",
                "http://192.168.1.73/resources/ffanime/1004.jpg",
                "http://192.168.1.73/resources/ffanime/1005.jpg",
                "http://192.168.1.73/resources/ffanime/1006.jpg",
                "http://192.168.1.73/resources/ffanime/1007.jpg",
                "http://192.168.1.73/resources/ffanime/1008.jpg",
                "http://192.168.1.73/resources/ffanime/1009.jpg"
            ],
            "audios": [
                "http://192.168.1.73/resources/ffanime/1000.mp3",
                "http://192.168.1.73/resources/ffanime/1001.mp3",
                "http://192.168.1.73/resources/ffanime/1002.mp3",
                "http://192.168.1.73/resources/ffanime/1003.mp3",
                "http://192.168.1.73/resources/ffanime/1004.mp3",
                "http://192.168.1.73/resources/ffanime/1005.mp3",
                "http://192.168.1.73/resources/ffanime/1006.mp3",
                "http://192.168.1.73/resources/ffanime/1007.mp3",
                "http://192.168.1.73/resources/ffanime/1008.mp3",
                "http://192.168.1.73/resources/ffanime/1009.mp3"
            ],
            "background_audio": "http://192.168.1.73/resources/ffanime/background.mp3",
            "opening": "http://192.168.1.73/resources/ffanime/0000.mp4",
            "cover": "http://192.168.1.73/resources/ffanime/cover.jpg"
        }
    """
    
    date_str, uid = datetime.now().strftime("%Y%m%d"), uuid.uuid4()
    work_dir, output_dir = f"/tmp/{uid}", f"{_OUTPUT_DIR}/{date_str}"

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

    if request.response_type == "url":
        return {"video": f"{_HTTP_PREFIX}/{final_output_path.replace(_OUTPUT_DIR, '').lstrip('/')}"}
    else:
        return {"video": final_output_path.replace(_OUTPUT_DIR, _PATH_PREFIX)}


if __name__ == "__main__":
    def _signal_handler(sig, frame):
        executor.shutdown(wait=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    uvicorn.run("main:app", host="0.0.0.0", port=8686, workers=2)
