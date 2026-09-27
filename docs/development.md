# Development Guide — AI Video Studio

## Environment Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- FFmpeg 5.0+ installed locally

### 2. Backend Environment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Environment
```bash
cd frontend
npm install
npm run dev
```

### 4. Background Workers (Optional Redis + Celery)
```bash
# Start Redis
redis-server

# Run Celery Worker
cd backend
./venv/bin/celery -A app.workers.celery_worker worker --loglevel=info
```

### 5. Running Tests
```bash
cd backend
./venv/bin/pytest -v tests/
```
