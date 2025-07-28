# Use an official, lightweight Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependency list
COPY requirements.txt .

# Install dependencies
# This happens during the build, so no network is needed at runtime.
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code into the container
COPY . .

# Set the command to run your script when the container starts
CMD ["python", "extract_outline.py"]