# Use a Debian-based image suitable for GitHub Codespaces
FROM debian:bullseye-slim

# Install necessary packages including Docker dependencies
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    git \
    ca-certificates \
    gnupg \
    lsb-release \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce docker-ce-cli containerd.io \
    && rm -rf /var/lib/apt/lists/*

# Install Tilt
RUN curl -fsSL https://github.com/tilt-dev/tilt/releases/download/v0.33.17/tilt.0.33.17.linux.x86_64.tar.gz | tar -xzv tilt && \
    mv tilt /usr/local/bin/tilt

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x ./kubectl && \
    mv ./kubectl /usr/local/bin/kubectl

# Install kind
RUN curl -Lo ./kind "https://kind.sigs.k8s.io/dl/v0.11.1/kind-linux-amd64" && \
    chmod +x ./kind && \
    mv ./kind /usr/local/bin/kind

# Install ctlptl
RUN CTLPTL_VERSION="0.8.29" && \
    curl -fsSL https://github.com/tilt-dev/ctlptl/releases/download/v$CTLPTL_VERSION/ctlptl.$CTLPTL_VERSION.linux.x86_64.tar.gz | \
    tar -xzv -C /usr/local/bin ctlptl

# Cleanup
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*