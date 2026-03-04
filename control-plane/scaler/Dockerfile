FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python files from current directory
COPY *.py ./

# Expose metrics port
EXPOSE 8001

# Run the main application
CMD ["python", "-u", "main.py"]
