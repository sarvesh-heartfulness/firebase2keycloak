# Use a specific Python version for the base image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the Python script into the container
COPY create-users.py .

# Install the dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
