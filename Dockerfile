FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim

WORKDIR /ffanime

RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

COPY requirements.txt .

RUN uv pip install --system -r requirements.txt

RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY . .

ENTRYPOINT ["python", "main.py"]
