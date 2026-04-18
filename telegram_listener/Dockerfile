# Use an official Python runtime as a parent image
FROM python:3.11-alpine
RUN echo "--- Build Started ---"
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY main.py .

# Run main.py when the container launches
CMD ["python", "main.py"]
