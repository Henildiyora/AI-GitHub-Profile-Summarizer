# Start from an official Python 3.11 image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /code

# Copy your requirements file first
COPY requirements.txt .

# Upgrade pip and install all dependencies in one go
# This is more efficient and uses the Docker cache better.
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire application code into the container
COPY . .

# Expose the correct port
EXPOSE 8000

# The command to run your application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]