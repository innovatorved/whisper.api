FROM python:3.10-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Create non-root user
RUN useradd -m -u 1000 user

# Set working directory
WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    git \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Optimize layer caching for python dependencies
COPY --chown=user:user requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Switch to non-root user
USER user
WORKDIR $HOME/app

# Copy application code
ARG CACHEBUST=1
RUN echo "Cache bust: $CACHEBUST"
COPY --chown=user:user . $HOME/app

# Build whisper binary from source
# Run setup_whisper_new.sh with cache-busting comment
RUN ls -la && chmod +x ./setup_whisper_new.sh && ./setup_whisper_new.sh

# Expose the API port (standard for HF Spaces)
EXPOSE 7860

# Default command to run the API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]