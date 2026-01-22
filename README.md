
# Build System for Open-Source Artifacts

This project, `zlinux-artifacts-builder`, is a modular, Dockerized build system designed to automate the generation, checksum, and publishing of software artifacts optimized for the s390x architecture (IBM Z mainframes). It supports building from GitHub repositories, integrating with build scripts from repositories like [linux-on-ibm-z](https://github.com/linux-on-ibm-z/scripts), can handle multiple artifact types (binaries, Debian packages, RPM packages, container images). The system is template-based, allowing easy addition of new repositories under a GitHub organization, and supports various programming languages (Go, C/C++, Java, Python) for binary artifacts.

## Features
- **Modular Builders**: Separate builders for binaries (language-specific), scipts, which can be extended to build Debian packages, RPM packages, and container images.
- **Template-Based Configuration**: Reusable templates for artifact definitions, with overrides per repository.
- **Script Integration**: Supports build scripts from multiple repositories, defaulting to [linux-on-ibm-z](https://github.com/linux-on-ibm-z/scripts) for s390x-specific builds.
- **s390x Compatibility**: All builds run in `s390x` Docker containers.
- **Automated Publishing**: Publishes to GitHub Releases (binaries, Debian, RPMs) and GHCR (container images).
- **Logging and Checksums**: Centralized logging and SHA256 checksums for artifact integrity.
- **Extensibility**: Easy to add new languages, artifact types, or script repositories.

## License
This project is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.

## Requirements
- **Operating System**: Linux IBM Z or LinuxONE (tested on Ubuntu 22.04 or later).
- **Docker**: For containerized builds (version 22.04 or later).
- **Python**: 3.10 or later.
- **GitHub Token**: With `repo` and `write:packages` scopes for cloning, scanning, and publishing.
- **GitHub CLI (`gh`)**: For publishing to Releases (installed in Docker image).
- **Python Dependencies**: Listed in `requirements.txt` (e.g., `pyyaml`, `requests`).

_*Note:*_ _Linux IBM Z or LinuxONE `s390x` architecture is required to build the project (if you do not have access to this architecture, you may request a virtual server via the [IBM LinuxONE Community Cloud](https://community.ibm.com/zsystems/l1cc/)._

## Setup Steps
To get the system working, follow these steps. The system runs in a Docker container to ensure consistency.

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/linuxonzapps/zlinux-artifacts-builder.git
   cd zlinux-artifacts-builder

2.  **Set Up Environment Variables**:
    
    -   Create a GitHub personal access token with `repo` and `write:packages` scopes.
    -   Set it as an environment variable:
        
        ```bash
        export GITHUB_TOKEN=your_github_token_here
        
        ```
        
3.  **Install Python Dependencies** (for manual testing outside Docker):
    
    ```bash
    pip install -r requirements.txt
    
    ```
    
4.  **Configure the System**:
    
    -   Edit `config/global_config.yaml` to specify your GitHub organization, repositories, and script repositories. Example:
        
        ```yaml
        organization: linuxonzapps
        scan_organization: false  # Set to true to scan all repos in linuxonzapps
        repositories:
          - name: test
            url: https://github.com/linuxonzapps/test
            template: templates/go-project.yaml
        default_schedule: "0 0 * * *"
        default_webhook: false
        script_repositories:
          - name: linux-on-ibm-z-scripts
            url: https://github.com/linux-on-ibm-z/scripts
          - name: custom-scripts
            url: https://github.com/linuxonzapps/custom-scripts
        
        ```
        
    -   Create or edit templates in `config/templates/`. Example (`go-project.yaml`):
        
        ```yaml
        artifacts:
          - type: binary
            language: go
            build_script:
              repo_name: linux-on-ibm-z-scripts
              path: Go/1.21/build_go.sh
              args: ["--version", "1.21"]
              docker_image: ubuntu:20.04
          - type: rpm
          - type: container
            image_name: "{{repo_name}}"
            dockerfile: Dockerfile
            registry: ghcr.io
        architecture: s390x
        schedule: "{{global_schedule}}"
        webhook: "{{global_webhook}}"
        
        ```
        
    -   For each repository (e.g., `linuxonzapps/test`), add `.build-template.yaml`:
        
        ```yaml
        template: go-project.yaml
        overrides:
          artifacts:
            - type: binary
              build_script:
                repo_name: custom-scripts
                path: custom_go_build.sh
                args: ["--custom-flag"]
                docker_image: ubuntu:22.04
        
        ```
        
5.  **Build the Docker Image**:
    
    ```bash
    docker build -t zlinux-artifacts-builder .
    
    ```

6. **Run the System**:
   - To build all repositories in `global_config.yaml`:
     ```bash
     docker run --rm --privileged -v /tmp:/tmp -v $(pwd):/app -v /var/run/docker.sock:/var/run/docker.sock -e GH_TOKEN=$GH_TOKEN -e PYTHONPATH=${PYTHONPATH}:/app zlinux-artifacts-builder
     ```
   - To build specific repositories (e.g., only `test`):
     ```bash
     docker run --rm --privileged -v /tmp:/tmp $(pwd):/app -v /var/run/docker.sock:/var/run/docker.sock -e GH_TOKEN=$GH_TOKEN -e PYTHONPATH=${PYTHONPATH}:/app zlinux-artifacts-builder config/global_config.yaml test
     ```
   - To build multiple specific repositories (e.g., `test` and `NewProject`):
     ```bash
     docker run --rm --privileged -v /tmp:/tmp -v $(pwd):/app -v /var/run/docker.sock:/var/run/docker.sock -e GH_TOKEN=$GH_TOKEN -e PYTHONPATH=${PYTHONPATH}:/app zlinux-artifacts-builder config/global_config.yaml test NewProject
     ```
   - The `--privileged` and `-v /var/run/docker.sock:/var/run/docker.sock` flags enable Docker-in-Docker for builds.
   - The orchestrator processes only the specified repositories (or all if none specified), building artifacts using scripts from `linux-on-ibm-z/scripts` or `custom-scripts`, and publishes them.
    
7.  **Test with CI/CD**:
    
    -   Push changes to `zlinux-artifacts-builder` to trigger `ci/ci_github_actions.yml`.
    -   For repository webhooks, configure webhooks in `linuxonzapps/test` to point to `zlinux-artifacts-builder`'s dispatch endpoint.
8.  **Verify Outputs**:
    
    -   Check `logs/build_system_YYYYMMDD_HHMMSS.log` for build logs.
    -   Artifacts in GitHub Releases (`https://github.com/linuxonzapps/test/releases`): `test_1.0.0_s390x`, `test-1.0.0-1.s390x.rpm`, `.sha256` files.
    -   Container in GHCR: `docker pull ghcr.io/linuxonzapps/test:1.0.0-s390x`.

## Directory Structure

The project is intended to be organized as follows:

```
zlinux-artifacts-builder/
├── builders/                 # Builder classes for artifacts
│   ├── binary/               # Add Language-specific binary builders, for example:
│   │   ├── go_binary_builder.py
│   │   ├── cpp_binary_builder.py (implement as needed)
│   │   ├── java_binary_builder.py (implement as needed)
│   │   ├── python_binary_builder.py (implement as needed)
│   │   └── __init__.py
│   ├── container/           # Container builder - (implement as needed)
│   ├── debian/              # Debian package builder - (implement as needed)
│   ├── rpm/                 # RPM package builder - (implement as needed)
│   ├── plugins/             # Builder interface
│   ├── script/              # Script builder
│   │   ├── loz_script_builder.py
│   │   └── __init__.py
│   └── __init__.py
├── ci/                      # CI/CD configuration
│   ├── ci_github_actions.yml
│   └── __init__.py
├── config/                  # Configuration files
│   ├── global_config.yaml
│   ├── templates/           # Artifact templates
│   │   ├── loz-script-project.yaml
│   │   ├── custom-project.yaml
│   │   └── __init__.py
│   └── __init__.py
├── containers/              # Supporting conatiners
│   ├── dind/                # Docker-in-Docker
│   │   ├── Dockerfile
├── lib/                     # Utility modules
│   ├── github_api.py
│   ├── versioning.py
│   ├── checksum.py
│   └── __init__.py
├── logs/                    # Runtime-generated logs
├── monitoring/              # Logging utilities
│   ├── logger.py
│   └── __init__.py
├── orchestrator/            # Orchestration logic
│   ├── orchestrator.py
│   └── __init__.py
├── Dockerfile               # Docker image definition
├── README.md                # This file
├── requirements.txt         # Python dependencies
└── __init__.py

```

## Troubleshooting

-   **No Output**: Ensure `global_config.yaml` lists `test` or `scan_organization: true`. Check logs for errors.
-   **Missing Scripts**: Verify script paths exist in the cloned repositories (e.g., `/tmp/linux-on-ibm-z-scripts/Go/1.21/build_go.sh`).
-   **Permission Errors**: Ensure `GITHUB_TOKEN` has correct scopes.
-   **Indentation Errors**: Use consistent 4-space indentation in Python files.
-   **Multiple Logs**: The singleton logger in `logger.py` prevents duplicates.

## Adding a New Repository

1.  Create `linuxonzapps/NewProject` from `s390x-project-template`.
2.  Update `.build-template.yaml` to reference a template (e.g., `go-project.yaml`).
3.  Add source files (e.g., `main.go`, `Dockerfile`).
4.  If not using scanning, add to `global_config.yaml`:
    
    ```yaml
    repositories:
      - name: NewProject
        url: https://github.com/linuxonzapps/NewProject
        template: templates/go-project.yaml
    
    ```
    
5.  Run the system to build artifacts.

## Extending the System

-   **New Templates**: Add YAML files in `config/templates/` for different project types (e.g., `java-project.yaml`).
-   **New Script Repositories**: Add to `global_config.yaml` under `script_repositories`.
-   **New Languages**: Add builders in `builders/binary/` (e.g., `rust_binary_builder.py`) and update `_load_builders` in `orchestrator.py`.
-   **New Artifact Types**: Add builders in `builders/` (e.g., `snap_builder.py`) and update `_load_builders`.

If you encounter issues, check `logs/` or open an issue on the repository. Contributions are welcome!
