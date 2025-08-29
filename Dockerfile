# Dockerfile
FROM python:3.11-slim

# Dependências do sistema para Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates libnss3 libatk-bridge2.0-0 libgtk-3-0 \
    libasound2 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libpango-1.0-0 libatk1.0-0 libcups2 libxshmfence1 libxfixes3 libatspi2.0-0 \
    fonts-liberation libu2f-udev xvfb \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala o Chromium do Playwright com todas as dependências
RUN python -m playwright install --with-deps chromium

COPY . .

ENV STREAMLIT_SERVER_PORT=10000
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLECORS=false

EXPOSE 10000

CMD ["streamlit", "run", "app.py", "--server.port=10000", "--server.address=0.0.0.0"]
