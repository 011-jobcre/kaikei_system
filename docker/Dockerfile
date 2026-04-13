# ==========================================
# STAGE 1: Build CSS (Using Node.js)
# ==========================================
FROM node:20-slim AS css-builder
WORKDIR /build

# Only copy files needed to install libraries
COPY package*.json ./

# install tailwind and daisyui
RUN npm install tailwindcss @tailwindcss/cli daisyui@latest @tailwindcss/typography

# Copy source code and build CSS
COPY backend/static/ ./backend/static/
COPY backend/templates ./backend/templates/

# Build CSS (Tailwind will find daisyui in node_modules)
RUN npx tailwindcss -i ./backend/static/css/input.css -o ./output.css --minify

# ==========================================
# STAGE 2: Runtime (Using Python)
# ==========================================
FROM python:3.12-slim

WORKDIR /app

# 1. Install system libraries needed for Django & PDF/Image
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. COPY FROM STAGE 1
# Copy the compiled CSS into the correct backend static folder
COPY --from=css-builder /build/output.css ./backend/static/css/output.css

# 4. Copy Django project code
COPY . .

# 5. Set up User and Permissions
WORKDIR /app/backend
RUN useradd -m appuser && chown -R appuser /app
COPY --chown=appuser:appuser docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser
EXPOSE 8000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBUG=False

ENTRYPOINT ["/entrypoint.sh"]
