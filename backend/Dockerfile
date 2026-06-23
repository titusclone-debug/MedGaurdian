# Use official Python runtime as a base image
FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies (including standard build utilities)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn for high-concurrency production processes
RUN pip install --no-cache-dir gunicorn

# Copy the entire backend source code
COPY . .

# Expose port 8000 for the app
EXPOSE 8000

# Apply the recorded schema revision under a PostgreSQL advisory lock before
# accepting traffic, then replace the shell so signals reach Gunicorn.
CMD ["sh", "-c", "python scripts/run_migrations.py && exec gunicorn -w 1 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000"]
