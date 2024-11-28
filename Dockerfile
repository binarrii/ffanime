FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim

WORKDIR /ffanime

COPY . .

RUN <<EOF
apt-get update && apt-get install ffmpeg && apt-get clean
uv pip install --system -r requirements.txt
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
EOF

ENTRYPOINT ["python", "api.py"]

