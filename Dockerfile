FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installation du package local
COPY pyproject.toml .
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# Application et artefacts gelés
COPY app/ ./app/
COPY models/ ./models/

EXPOSE 8501

CMD ["streamlit", "run", "app/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--server.fileWatcherType=none"]