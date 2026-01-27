#  Copyright Contributors to the Mainframe Software Hub for Linux Project.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from monitoring.logger import Logger
from builders.plugins.plugin_interface import ArtifactBuilder

BUILD_SYSTEMS = {
    "maven": {
        "files": ["pom.xml"],
        "command": ["mvn", "-DskipTests", "clean", "package"],
        "build_dir": "target",
        "docker_image": "maven:3.9-eclipse-temurin-17",
    },
    "gradle": {
        "files": ["build.gradle", "build.gradle.kts"],
        "command": ["gradle", "clean", "build", "-x", "test"],
        "build_dir": os.path.join("build", "libs"),
        "docker_image": "gradle:8.7-jdk17",
    },
}

def detect_build_system(repo_path: str):
    for system, config in BUILD_SYSTEMS.items():
        for f in config["files"]:
            if os.path.exists(os.path.join(repo_path, f)):
                return system, config
    return None, None

class JavaBinaryBuilder(ArtifactBuilder):
    def __init__(self):
        self.logger = Logger()

    def build(self, repo_path: str, repo_gh_name: str, artifact: dict) -> str:
        version = artifact.get("version", "1.0")
        output_dir = os.path.join(repo_path, "build")
        output_path = os.path.join(output_dir, f"{repo_gh_name}_{version}_s390x.jar")

        os.makedirs(output_dir, exist_ok=True)

        system, config = detect_build_system(repo_path)
        if not system:
            raise RuntimeError(
                f"No supported Java build file found in {repo_path}. "
                f"Expected one of: {', '.join(sum([v['files'] for v in BUILD_SYSTEMS.values()], []))}"
            )

        docker_image = artifact.get("docker_image", config["docker_image"])
        cmd = config["command"]
        build_dir = os.path.join(repo_path, config["build_dir"])

        try:
            self.logger.info(f"Building Java artifact using {system} for {repo_gh_name}")

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

            jars = [
                os.path.join(build_dir, f)
                for f in os.listdir(build_dir)
                if f.endswith(".jar")
                and not f.endswith("-sources.jar")
                and not f.endswith("-javadoc.jar")
            ]

            if not jars:
                raise RuntimeError(f"No runnable JAR found in {build_dir}")

            subprocess.run(["cp", jars[0], output_path], check=True)

            self.logger.info(f"Built Java artifact at {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to build Java artifact for {repo_gh_name}: {str(e)}")
            raise
