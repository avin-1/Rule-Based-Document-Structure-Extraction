FROM python:3.9-slim

WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the script
CMD ["python", "extract_outline.py", "/app/input/sample.pdf", "/app/output/output.json"]