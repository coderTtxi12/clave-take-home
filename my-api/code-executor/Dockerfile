FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install essential data science packages + PostgreSQL adapter
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pandas \
    numpy \
    matplotlib \
    seaborn \
    scikit-learn \
    scipy \
    requests \
    plotly \
    psycopg2-binary \
    sqlalchemy \
    tabulate

# Create data directory first
RUN mkdir -p /app/data/outputs

# Copy the executor service and database helper
COPY executor.py .
COPY db_helper.py .

# Run as non-root user for security
RUN useradd -m -u 1000 executor && chown -R executor:executor /app
USER executor

# Expose port
EXPOSE 8001

# Run the service
CMD ["uvicorn", "executor:app", "--host", "0.0.0.0", "--port", "8001"]

