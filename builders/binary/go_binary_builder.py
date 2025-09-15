#  Copyright Contributors to the Mainframe Software Hub for Linux Project.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from monitoring.logger import Logger
from builders.plugins.plugin_interface import ArtifactBuilder

class GoBinaryBuilder(ArtifactBuilder):
    def __init__(self):
        self.logger = Logger()

    def build(self, repo_path: str, repo_gh_name: str, artifact: dict) -> str:
        repo_name = os.path.basename(repo_path)
        version = artifact.get('version', '1.0')
        output_path = f"{repo_path}/build/{repo_gh_name}_{version}_s390x"

        try:
            os.makedirs("build", exist_ok=True)
            cmd = ["go", "build", "-o", output_path, "."]
            self.logger.info(f"Building Go binary for {repo_gh_name}")
            docker_image = artifact.get('docker_image', 'ubuntu:22.04')
            subprocess.run(
                    ["docker", "run", "--rm", "-v", f"{repo_path}:{repo_path}", "-v", f"{repo_path}:/app", "-w", "/app", docker_image] + cmd,
                check=True
            )
            self.logger.info(f"Built Go binary at {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to build Go binary for {repo_name}: {e.stderr.decode()}")
            raise

    def publish(self, artifact_path: str, repo_gh_name: str, artifact:dict):
        from lib.checksum import generate_checksum
        checksum = generate_checksum(artifact_path)
        version = artifact.get('version', '1.0')
        self.logger.info(f"Publishing {artifact_path} with checksum {checksum} for {repo_gh_name}")
        try:
            subprocess.run(
                ["gh", "release", "create", f"v{version}", "--title", f"Version {version}", "--generate-notes", artifact_path, f"{artifact_path}.sha256"],
                cwd=os.path.dirname(artifact_path),
                check=True
            )
            self.logger.info(f"Published {artifact_path} to GitHub Releases")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to publish {artifact_path}: {e.stderr.decode()}")
            raise
