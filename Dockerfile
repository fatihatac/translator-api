# Use the specific Python 3.14.0 runtime as a parent image (slim version)
FROM python:3.14.0-slim

# Set environment variables to optimize Python execution in Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install dependencies securely without keeping cache to save space
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the entire project directory into the container
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]