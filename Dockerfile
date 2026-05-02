FROM python:3.10-slim

WORKDIR /app

# Install dependencies first (better Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Don't run as root inside the container
RUN useradd -m appuser
USER appuser

# Expose port
EXPOSE 5000

# Use Gunicorn (production WSGI server), NOT Flask's dev server
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "--timeout", "120", "--access-logfile", "-", "app:app"]
