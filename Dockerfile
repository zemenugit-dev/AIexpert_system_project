# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies (SWI-Prolog) as root
RUN apt-get update && apt-get install -y \
    swi-prolog \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port your Flask app runs on (Render assigns this via $PORT)
EXPOSE 10000

# Start the application using python app.py
# Change this line at the bottom of your Dockerfile:
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]