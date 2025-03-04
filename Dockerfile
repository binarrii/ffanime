FROM ubuntu:22.04

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/bin/

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /ffanime

RUN apt-get update && apt-get install -y python3.10 ffmpeg curl && apt-get clean

COPY requirements.txt .

RUN uv pip install --system --no-cache-dir -r requirements.txt

RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY . .

ENTRYPOINT ["python3.10", "main.py"]
