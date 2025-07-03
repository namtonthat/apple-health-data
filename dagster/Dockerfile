FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the entire project
COPY . /app/

# Install uv
RUN pip install uv

# Install project dependencies including Dagster
RUN cd /app && uv sync --all-groups

# Expose Dagster web server port
EXPOSE 3000

# Set environment variables
ENV DAGSTER_HOME=/app/dagster

# Run Dagster web server
CMD ["uv", "run", "dagster-webserver", "-h", "0.0.0.0", "-p", "3000", "-w", "workspace.yaml"]