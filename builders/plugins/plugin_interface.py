#  Copyright Contributors to the Mainframe Software Hub for Linux Project.
#  SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod

class ArtifactBuilder(ABC):
    @abstractmethod
    def build(self, repo_path: str, repo_name: str, artifact: dict) -> str:
        """Builds the artifact and returns its path."""
        pass

    @abstractmethod
    def publish(self, artifact_path: str, repo_name: str, artifact: dict) -> None:
        """Publishes the artifact to its destination."""
        pass
