FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY config/ ./config/
COPY utils/ ./utils/
COPY parser/ ./parser/
COPY database/ ./database/
COPY main.py .
COPY query.py .
COPY example-queries.py .

#RUN mkdir -p temp_repo


RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

#CMD ["python", "example-queries.py"]
CMD ["python", "main.py"]