# Dockerfile for a secure Python code execution server using FastAPI
FROM python:3.11-slim

# Install FastAPI and Uvicorn
RUN pip install fastapi 'uvicorn[standard]' docker

# Create app directory
WORKDIR /app

# Copy server code
COPY server.py /app/server.py

# Add a non-root user for security
ARG DOCKER_GID=999
RUN groupadd -g $DOCKER_GID docker && useradd -m -g docker appuser && usermod -aG docker appuser
USER appuser

# Expose port
EXPOSE 8000

# Note: For extra security, run the container with --network=none to block network access for executed code
# Example:
# docker run --memory=128m --cpus=0.5 --network=none -p 3265:8000 python-exec-server

# Run the FastAPI server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
