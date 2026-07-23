# Use the official Langflow image as the base
FROM langflowai/langflow:latest

# Switch to root user temporarily to install packages
USER root

# Install your required pip package (e.g., 'transformers')
# Use the path to the virtual environment's pip executable

RUN /app/.venv/bin/pip install clickhouse-sqlalchemy

# Switch back to the default user for security
USER user
