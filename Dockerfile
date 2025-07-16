FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /code/

# Create necessary directories
RUN mkdir -p /code/logs /code/media /code/static

# Run collectstatic (if needed)
# RUN python manage.py collectstatic --noinput

# Run as non-root user
RUN useradd -m yooini && chown -R yooini:yooini /code
USER yooini

# Default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]