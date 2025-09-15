# Docker-in-Docker (DinD)

## Overview

This setup provides a way to create Docker-in-Docker (DinD) image for `s390x` architecture.

## Getting Started

### Prerequisites

- Docker installed on your host machine.

### Usage

1.  **Build the Docker Image:**

    ```bash
    docker build -t dind:s390x .

2. **Launch the container, for example:**
   ```bash
   docker run --privileged --name my-dind-container -d dind:s390x
