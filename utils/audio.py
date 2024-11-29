import av
from typing import Optional


def get_duration(file_path: Optional[str]) -> float:
    if file_path is None:
        return 0
    with av.open(file_path) as audio:
        duration = audio.duration / av.time_base
    return duration
