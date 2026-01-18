# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies for PPT processing and audio
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create a directory for temporary PPT processing
RUN mkdir -p workdir

# Expose the port FastAPI runs on
EXPOSE 8000

# Script to decide whether to run the API or the Agent
# Render will use the 'Command' field to override this
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]