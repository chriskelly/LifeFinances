FROM python:3.10

# Install system dependencies if needed
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Copy requirements first for better caching
COPY requirements/ /requirements/

# Install development dependencies
RUN pip install --no-cache-dir -r /requirements/dev.txt

# Copy application code
COPY . /workspace/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command
CMD ["/bin/bash"]
