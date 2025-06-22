FROM python:3.11-slim-bookworm AS builder
WORKDIR /app

# Install all MuPDF & image libs in one go
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential gcc pkg-config \
    libmupdf-dev libfreetype6-dev libjpeg-dev zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip, then install requirements
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt


# ─── Stage 2: Final ───────────────────────────────────────
FROM python:3.11-slim-bookworm

WORKDIR /app

COPY --from=builder /usr/local /usr/local
COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
