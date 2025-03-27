# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that the application will run on
EXPOSE 5000

# Set environment variables for MQTT broker
ENV MQTT_BROKER_HOST=mqtt-broker
ENV MQTT_BROKER_PORT=1883

# Run the application
CMD ["python", "app.py"]