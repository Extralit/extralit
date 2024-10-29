# Use a Debian-based image suitable for GitHub Codespaces
FROM debian:bullseye-slim

# Copy the devcontainer setup file into the container
COPY *.sh /workspace/
RUN chmod +x /workspace/*.sh

RUN mkdir -p /etc/docker && \
    echo '{"data-root": "/tmp/docker"}' > /etc/docker/daemon.json && \
    chown -R root:docker /etc/docker && \
    chmod -R 755 /etc/docker

# Install necessary packages including Docker dependencies
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    git \
    ca-certificates \
    gnupg \
    lsb-release \
    cron \
    && apt-get update \
    && rm -rf /var/lib/apt/lists/*

# Install Tilt
RUN curl -fsSL https://github.com/tilt-dev/tilt/releases/download/v0.33.17/tilt.0.33.17.linux.x86_64.tar.gz | tar -xzv tilt && \
    mv tilt /usr/local/bin/tilt

# Install ctlptl
RUN CTLPTL_VERSION="0.8.31" && \
    curl -fsSL https://github.com/tilt-dev/ctlptl/releases/download/v$CTLPTL_VERSION/ctlptl.$CTLPTL_VERSION.linux.x86_64.tar.gz | \
    tar -xzv -C /usr/local/bin ctlptl

