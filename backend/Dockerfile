FROM python:3.11-slim

WORKDIR /app

# Install requirements FIRST (cached layer — only re-runs if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source AFTER (changes here don't bust the pip cache)
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
