FROM python:3.11-slim

# Install system dependencies and Bun
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    git \
    passwd \
    && rm -rf /var/lib/apt/lists/*

# Install Bun globally and make it accessible to all users
RUN curl -fsSL https://bun.sh/install | bash && \
    cp /root/.bun/bin/bun /usr/local/bin/bun && \
    chmod +x /usr/local/bin/bun && \
    ln -s /usr/local/bin/bun /usr/local/bin/bunx || true
ENV PATH="/usr/local/bin:/root/.bun/bin:${PATH}"

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

# Create data directory and Next.js project directory
RUN mkdir -p /app/data/outputs && \
    mkdir -p /home/user

# Create Next.js project in /home/user
WORKDIR /home/user
# Use bun x instead of bunx, and ensure PATH is set
RUN export PATH="/usr/local/bin:/root/.bun/bin:$PATH" && \
    /usr/local/bin/bun x create-next-app@15.5.0 . --ts --tailwind --no-eslint --import-alias "@/*" --yes && \
    /usr/local/bin/bun x shadcn@2.10.0 init -b neutral -y && \
    /usr/local/bin/bun x shadcn@2.10.0 add --all && \
    /usr/local/bin/bun add recharts chart.js d3 && \
    /usr/local/bin/bun add -d @types/d3

# Return to /app for the service
WORKDIR /app

# Copy the executor service and database helper
COPY executor.py .
COPY db_helper.py .

# Create executor user for security (with shell)
# Check if user exists first, create if not
RUN (id -u executor 2>/dev/null || useradd -m -u 1000 -s /bin/bash executor) && \
    chown -R executor:executor /app && \
    chown -R executor:executor /home/user

# Create startup script to run both services
RUN echo '#!/bin/bash\n\
set -e\n\
# Function to start Next.js with auto-restart\n\
start_nextjs() {\n\
  cd /home/user\n\
  while true; do\n\
    echo "Starting Next.js dev server..."\n\
    bun run dev >> /tmp/nextjs.log 2>&1 || true\n\
    echo "Next.js process exited, restarting in 5 seconds..."\n\
    sleep 5\n\
  done\n\
}\n\
\n\
# Start Next.js in background with auto-restart\n\
start_nextjs &\n\
NEXTJS_PID=$!\n\
echo "Next.js started with PID $NEXTJS_PID on port 3000"\n\
\n\
# Wait a bit for Next.js to start\n\
sleep 5\n\
\n\
# Start FastAPI server (this blocks)\n\
cd /app\n\
exec uvicorn executor:app --host 0.0.0.0 --port 8001\n\
' > /app/start.sh && chmod +x /app/start.sh && \
    chown executor:executor /app/start.sh

USER executor

# Expose ports
EXPOSE 8001 3000

# Run the service
CMD ["/app/start.sh"]

