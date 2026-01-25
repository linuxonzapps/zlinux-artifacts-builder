#  Copyright Contributors to the Mainframe Software Hub for Linux Project.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from monitoring.logger import Logger
from builders.plugins.plugin_interface import ArtifactBuilder


class JavaBinaryBuilder(ArtifactBuilder):
    def __init__(self):
        self.logger = Logger()

    def build(self, repo_path: str, repo_gh_name: str, artifact: dict) -> str:
        repo_name = os.path.basename(repo_path)
        version = artifact.get("version", "1.0")

        output_path = f"{repo_path}/build/{repo_gh_name}_{version}.jar"

        docker_image = artifact.get("docker_image", "maven:3.9-eclipse-temurin-17")

        try:
            os.makedirs("build", exist_ok=True)

            self.logger.info(f"Building Java artifact for {repo_gh_name}")

            pom_path = os.path.join(repo_path, "pom.xml")
            gradle_path = os.path.join(repo_path, "build.gradle")
            gradle_kts_path = os.path.join(repo_path, "build.gradle.kts")

            is_maven = os.path.exists(pom_path)
            is_gradle = os.path.exists(gradle_path) or os.path.exists(gradle_kts_path)

            if not is_maven and not is_gradle:
                raise RuntimeError(
                    f"No supported Java build file found in {repo_path}. "
                    f"Expected pom.xml or build.gradle(.kts)."
                )

            if is_maven:
                cmd = ["mvn", "-DskipTests", "clean", "package"]

                expected_build_dir = os.path.join(repo_path, "target")

            else:
                cmd = ["gradle", "clean", "build", "-x", "test"]

                expected_build_dir = os.path.join(repo_path, "build", "libs")

            subprocess.run(
                [
                    "docker", "run", "--rm",
                    "-v", f"{repo_path}:{repo_path}",
                    "-v", f"{repo_path}:/app",
                    "-w", "/app",
                    docker_image,
                ] + cmd,
                check=True
            )

            jar_candidates = []
            if os.path.isdir(expected_build_dir):
                for f in os.listdir(expected_build_dir):
                    if f.endswith(".jar"):
                        jar_candidates.append(os.path.join(expected_build_dir, f))

            if not jar_candidates:
                raise RuntimeError(
                    f"No JAR produced. Looked in: {expected_build_dir}. "
                    f"TODO: Confirm build output paths / packaging."
                )

            chosen_jar = jar_candidates[0]

            subprocess.run(["cp", chosen_jar, output_path], check=True)

            self.logger.info(f"Built Java artifact at {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to build Java artifact for {repo_name}: {str(e)}")
            raise

    def publish(self, artifact_path: str, repo_gh_name: str, artifact: dict) -> None:
        from lib.checksum import generate_checksum

        checksum = generate_checksum(artifact_path)
        version = artifact.get("version", "1.0")

        self.logger.info(f"Publishing {artifact_path} with checksum {checksum} for {repo_gh_name}")

        try:
            subprocess.run(
                [
                    "gh", "release", "create", f"v{version}",
                    "--title", f"Version {version}",
                    "--generate-notes",
                    artifact_path,
                    f"{artifact_path}.sha256",
                ],
                cwd=os.path.dirname(artifact_path),
                check=True
            )
            self.logger.info(f"Published {artifact_path} to GitHub Releases")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to publish {artifact_path}: {str(e)}")
            raise
