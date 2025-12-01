#  Copyright Contributors to the Mainframe Software Hub for Linux Project.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from monitoring.logger import Logger
from builders.plugins.plugin_interface import ArtifactBuilder

class ScriptBuilder(ArtifactBuilder):
    def __init__(self):
        self.logger = Logger()
        self.script_repo_paths = {}  # Will be set by BuildOrchestrator

    def set_script_repo_paths(self, script_repo_paths: dict):
        self.script_repo_paths = script_repo_paths

    def execute_pipe_command(self, cmd1: str, cmd2: str):
        p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(cmd2, stdin=p1.stdout, stdout=subprocess.PIPE, text=True)
        p1.stdout.close()
        output, _ = p2.communicate()
        return output.strip()

    def build(self, repo_path: str, repo_gh_name: str, artifact: dict) -> str:
        build_script = artifact.get('build_script', {})
        version = artifact.get('version', '1.0')
        repo_name = build_script.get('repo_name', 'linux-on-ibm-z-scripts')
        script_path = build_script.get('path')
        if not script_path:
            self.logger.error("No build_script.path specified for ScriptBuilder")
            raise ValueError("build_script.path required")

        script_repo_path = self.script_repo_paths.get(repo_name)
        if not script_repo_path:
            self.logger.error(f"Script repository {repo_name} not found in cloned repositories")
            raise ValueError(f"Script repository {repo_name} not found")

        full_script_path = os.path.join(repo_path,script_path)
        if not os.path.exists(full_script_path):
            self.logger.error(f"Script {full_script_path} not found")
            raise FileNotFoundError(f"Script {full_script_path} not found")

        artifact_type = artifact.get('type', 'binary')
        repo_name = os.path.basename(repo_path)
        docker_required= build_script.get('docker_required')
        output_path = f"{repo_path}/{repo_gh_name}-{version}-linux-s390x.tar.gz"

        cmd = ["bash", full_script_path, f"version {version}", build_script.get('args', '')]
        docker_image = build_script.get('docker_image', 'ubuntu:22.04')
        try:
            self.logger.info(f"Running script {script_path} from {repo_name} for {repo_gh_name}")
            # Few scripts require Docker to be present
            if docker_required is not None:
                docker_user = os.environ.get('DOCKER_USERNAME')
                docker_pwd = os.environ.get('DOCKER_PASSWORD')
                gh_token = os.environ.get('GH_TOKEN')
                gh_push_user = os.environ.get('GH_PUSH_USER')
                subprocess.run(
                        ["docker", "run", "--rm", "-e", f"DOCKER_USERNAME={docker_user}", "-e", f"DOCKER_PASSWORD={docker_pwd}", "-e", f"GH_TOKEN={gh_token}", "-e", f"GH_PUSH_USER={gh_push_user}", "-v", "/var/run/docker.sock:/var/run/docker.sock", "-v", f"{repo_path}:{repo_path}", "-v", f"{script_repo_path}:{script_repo_path}", "-w", repo_path, docker_image] + cmd,
                    check=True
                )
            else:
                subprocess.run(
                        ["docker", "run", "--rm", "-v", f"{repo_path}:{repo_path}", "-v", f"{repo_path}:/app", "-v", f"{script_repo_path}:{script_repo_path}", "-w", "/app", docker_image] + cmd,
                    check=True
                )
            if not os.path.exists(output_path):
                self.logger.error(f"Expected output {output_path} not found")
                raise FileNotFoundError(f"Expected output {output_path} not found")
            self.logger.info(f"Built {artifact_type} for {repo_gh_name} using {script_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to run script {script_path}: {e.stderr.decode()}")
            raise

    def publish(self, artifact_path: str, repo_gh_name: str, artifact: dict):
        from lib.checksum import generate_checksum
        checksum = generate_checksum(artifact_path)
        art_dirname = os.path.dirname(artifact_path)
        version = artifact.get('version', '1.0')
        rpm_path = f"{art_dirname}/{repo_gh_name}-{version}-1.s390x.rpm" if os.path.exists(f"{art_dirname}/{repo_gh_name}-{version}-1.s390x.rpm") else None
        deb_path = f"{art_dirname}/{repo_gh_name}_{version}_s390x.deb" if os.path.exists(f"{art_dirname}/{repo_gh_name}_{version}_s390x.deb") else None
        container_path = f"{art_dirname}/{repo_gh_name}-{version}-linux-s390x.container.tar" if os.path.exists(f"{art_dirname}/{repo_gh_name}-{version}-linux-s390x.container.tar") else None
        self.logger.info(f"Publishing {artifact_path} with checksum {checksum}")
        try:
            subprocess.run(
                ["gh", "release", "create", f"v{version}", "--title", f"Version {version}", "--generate-notes", artifact_path, f"{artifact_path}.sha256"],
                cwd=os.path.dirname(artifact_path),
                check=True
            )
            if rpm_path is not None:
                subprocess.run(
                    ["gh", "release", "upload", f"v{version}", rpm_path],
                    cwd=os.path.dirname(artifact_path),
                    check=True
                )
            if deb_path is not None:
                subprocess.run(
                    ["gh", "release", "upload", f"v{version}", deb_path],
                    cwd=os.path.dirname(artifact_path),
                    check=True
                )
            if container_path is not None:
                registry = artifact.get('registry', 'ghcr.io')
                image_name = artifact.get('image_name', repo_gh_name)
                gh_token = os.environ.get('GH_TOKEN')
                gh_push_user = os.environ.get('GH_PUSH_USER') # linuxonzapps, for example
                docker_login_p1 = ["echo", f"{gh_token}"]
                docker_login_p2 = ["docker", "login", f"{registry}", "-u", gh_push_user, "--password-stdin"]
                docker_exec_pipe = self.execute_pipe_command(docker_login_p1, docker_login_p2)
                self.logger.info(f"docker login returned with: {docker_exec_pipe}")
                # Load image from tar
                load_cmd = ["docker", "load", "-i", container_path]
                # Obtain image tag and retag it with registry
                extract_image_tag_p1 = ["tar", "-xOf", f"{container_path}", "manifest.json"]
                extract_image_tag_p2 = ["jq", ".[].RepoTags[]"]
                image_tag = self.execute_pipe_command(extract_image_tag_p1, extract_image_tag_p2).strip('"')
                self.logger.info(f"Container image: {image_tag}")
                # Tag the image - e.g., docker tag $image_tag $registry/linuxonzapps/$image_tag
                image_tag_cmd = ["docker", "tag", f"{image_tag}", f"{registry}/{gh_push_user}/{image_tag}"]
                result = subprocess.run(image_tag_cmd, check=True, capture_output=True)
                # Push to registry
                push_cmd = ["docker", "push", f"{registry}/{gh_push_user}/{image_tag}"]
                subprocess.run(push_cmd, check=True, capture_output=True)
                self.logger.info(f"Published container image to {registry}/{gh_push_user}/{image_tag}")
            self.logger.info(f"Published {artifact_path} to GitHub Releases")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to publish {artifact_path}: {e.stderr.decode()}")
            raise
