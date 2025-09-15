# s390x Build Template

This is a GitHub repository template for building s390x artifacts (binaries, Debian packages, RPM packages, container images) using the `zlinux-artifacts-builder` system. It integrates with `linux-on-ibm-z/scripts` for s390x-specific builds.

## License
Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

## Getting Started
1. **Create a Repository from this Template**:
   - Click "Use this template" on GitHub to create a new repository (e.g., `linuxonzapps/NewProject`).
   - Ensure the repository is under the organization specified in `zlinux-artifacts-builder/config/global_config.yaml` (e.g., `linuxonzapps`).

2. **Customize Files**:
   - **`.build-template.yaml`**: Specifies the build template and artifacts. Default uses `go-project.yaml` for a Go binary and container. Update `overrides` for custom build scripts or registries.
     ```yaml
     template: go-project.yaml
     overrides:
       artifacts:
         - type: binary
           language: go
           build_script:
             path: Go/1.21/build_go.sh
             args: --version 1.21
             docker_image: ubuntu:20.04
         - type: container
           image_name: "{{repo_name}}"
           dockerfile: Dockerfile
           registry: ghcr.io
     ```
   - **`main.go`**: Replace with your Go source code.
   - **`Dockerfile`**: Update to match your container requirements.
   - **Add Other Files**: Include additional source files, build scripts, or configuration as needed.

3. **Integrate with Build System**:
   - Ensure `zlinux-artifacts-builder` is configured with:
     - `global_config.yaml` including your organization (`linuxonzapps`) and `scan_organization: true` or a specific repository entry:
       ```yaml
       organization: linuxonzapps
       scan_organization: true
       ```
     - A matching template in `zlinux-artifacts-builder/config/templates/go-project.yaml`.
   - The build system will:
     - Clone this repository.
     - Read `.build-template.yaml` to apply the `go-project.yaml` template.
     - Use `linux-on-ibm-z/scripts` (e.g., `Go/1.21/build_go.sh`) for builds.
     - Generate artifacts in Docker containers (`--platform=linux/s390x`).
     - Publish to GitHub Releases (binaries) and GHCR (containers).

4. **Trigger Builds**:
   - Builds run automatically via GitHub Actions in `zlinux-artifacts-builder/ci/ci_github_actions.yml` (hourly or on webhooks).
   - Manually trigger by running:
     ```bash
     cd zlinux-artifacts-builder
     docker build -t zlinux-artifacts-builder .
     docker run --rm --privileged -v $(pwd):/app -v /var/run/docker.sock:/var/run/docker.sock -e GITHUB_TOKEN=your_token zlinux-artifacts-builder
     ```

## Artifact Output
- **Binary**: `<repo_name>_<version>_s390x` (e.g., `newproject_1.0.0_s390x`) in GitHub Releases.
- **Container**: `ghcr.io/linuxonzapps/<repo_name>:<version>-s390x` (e.g., `ghcr.io/linuxonzapps/newproject:1.0.0-s390x`).

## Customizing for Other Languages
- Change the template in `.build-template.yaml` (e.g., `python-project.yaml` for Python projects).
- Update `main.go` to `main.py`, `Main.java`, etc., and adjust the `Dockerfile`.

## Requirements
- Source code compatible with `linux-on-ibm-z/scripts` (e.g., Go 1.21 for `Go/1.21/build_go.sh`).
- A `Dockerfile` for container artifacts.
- A GitHub token with `repo` and `write:packages` scopes in `zlinux-artifacts-builder`.
