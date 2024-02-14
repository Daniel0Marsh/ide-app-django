# Use an appropriate base image, such as Ubuntu
FROM ubuntu:latest

# Set the working directory in the container
WORKDIR /projects

# Install necessary packages for a terminal session
RUN apt-get update && apt-get install -y \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Set the default command to run when the container starts
CMD ["bash"]
