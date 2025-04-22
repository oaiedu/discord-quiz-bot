# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy only requirements first to leverage cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

CMD ["python", "bot.py"]