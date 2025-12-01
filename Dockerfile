# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
# If requirements.txt doesn't exist, we'll install streamlit directly for now, 
# but ideally we should have a requirements.txt. 
# I'll assume requirements.txt exists or create one in the next step if needed.
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Define environment variable
ENV NAME World

# Run app.py when the container launches
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
