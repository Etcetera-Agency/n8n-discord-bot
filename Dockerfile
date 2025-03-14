# Use an official Python slim image as the base image.
FROM python:3.10-slim

# Set the working directory in the container.
WORKDIR /app

# (Optional) Install system dependencies if needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements.txt file into the container.
COPY requirements.txt .

# Install Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container.
COPY . .

# Expose the port used by the web server (default is 3000)
EXPOSE 3000

# Set the command to run your bot.
CMD ["python", "main.py"]
