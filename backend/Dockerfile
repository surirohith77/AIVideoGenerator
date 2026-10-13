FROM python:3.11-slim

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-f5.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m venv /opt/f5-venv \
    && /opt/f5-venv/bin/pip install --no-cache-dir -r requirements-f5.txt
ENV F5_TTS_PYTHON=/opt/f5-venv/bin/python

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
