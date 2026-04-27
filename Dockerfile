FROM python:3.11-slim

WORKDIR /workspace

# 1. System-Abhängigkeiten installieren
# Neben build-essential brauchen wir für Playwright viele Grafik- und System-Libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libevent-2.1-7 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 2. Python-Abhängigkeiten (muss 'playwright' in der requirements.txt enthalten)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Playwright Browser-Binaries installieren
# Hier installieren wir Chromium. Falls ihr Firefox/Webkit braucht, einfach weglassen oder ergänzen.
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

EXPOSE 8501

# Der Command der beim Starten der Application laufen soll
CMD ["streamlit", "run", "dashboard/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]