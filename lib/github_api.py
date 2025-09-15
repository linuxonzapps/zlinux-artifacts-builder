#  Copyright Contributors to the Mainframe Software Hub for Linux Project.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
import tempfile
from monitoring.logger import Logger

class GitHubRepo:
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        self.logger = Logger()

    def clone(self, commit: str = "main") -> str:
        temp_dir = tempfile.mkdtemp()
        cmd = ["git", "clone", "--depth", "1", "--branch", commit, self.repo_url, temp_dir]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            self.logger.info(f"Cloned {self.repo_url} at commit {commit}")
            return temp_dir
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Clone failed: {e.stderr.decode()}")
            raise
