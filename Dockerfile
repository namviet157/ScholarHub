# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data (required for keywords extraction)
RUN python -c "import nltk; nltk.download('stopwords', quiet=True)"

# Copy the entire project
COPY . .

# Create necessary directories
RUN mkdir -p embeddings ArXivPapers

# Set Python path to include the project root
ENV PYTHONPATH=/app

# Default command - run the import script
CMD ["python", "processing/import_to_mongodb.py"]
