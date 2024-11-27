import av


def get_duration(file_path: str) -> float:
    with av.open(file_path) as container:
        duration = container.duration / av.time_base
    return duration
