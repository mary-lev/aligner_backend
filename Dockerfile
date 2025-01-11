FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for lxml and others
RUN apt-get update && apt-get install -y \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip install lxml
# Copy the current directory contents into the container at /app
COPY . /app/

# Install the required Python packages from requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose port (if needed for web apps)
EXPOSE 8000

# Run the application (you can change this according to your entry point)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
