# Use an appropriate base image, such as Ubuntu
FROM ubuntu:latest

# Install necessary packages for a terminal session
RUN apt-get update && apt-get install -y \
    bash \
    python3 \
    python3-pip \
    git \
    vim \
    curl \
    build-essential \
    wget \
    unzip \
    ca-certificates \
    lsb-release \
    software-properties-common \
    screen \
    tmux \
    && rm -rf /var/lib/apt/lists/*

# Set the user for running the container to the username of the host machine###
USER user

# Set the default command to run when the container starts
CMD ["bash"]

