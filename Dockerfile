# Use Ubuntu 20.04 as the base image for s390x compatibility
FROM dind:s390x

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    pkg-config \
    libssl-dev \
    git \
    curl \
    vim \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy build system files
COPY orchestrator/ orchestrator/
COPY builders/ builders/
COPY lib/ lib/
COPY monitoring/ monitoring/
COPY ci/ ci/
COPY requirements.txt .
COPY config/global_config.yaml config/global_config.yaml
COPY config/templates/ config/templates/

# Create lib/__init__.py to ensure lib is a Python package
RUN touch lib/__init__.py

# Install Python dependencies
RUN pip3 install maturin && pip3 install -r requirements.txt

# Ensure Docker socket is accessible
VOLUME /var/run/docker.sock

# Set entrypoint to run orchestrator with global_config.yaml
ENTRYPOINT ["python3", "/app/orchestrator/orchestrator.py"]
CMD ["config/global_config.yaml"]
