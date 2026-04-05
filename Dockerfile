FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libsndfile1 ffmpeg && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir pdm && pdm install --prod --no-lock --no-editable

# Pre-download SNAC model
RUN pdm run python -c "from snac import SNAC; SNAC.from_pretrained(\"hubertsiuzdak/snac_24khz\")"

COPY calldesnac.py .

ENTRYPOINT ["pdm", "run", "python", "calldesnac.py"]
