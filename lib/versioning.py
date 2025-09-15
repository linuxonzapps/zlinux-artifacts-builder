#  Copyright Contributors to the Mainframe Software Hub for Linux Project.
#  SPDX-License-Identifier: Apache-2.0

import subprocess
from monitoring.logger import Logger

def get_version(repo_path: str) -> str:
    logger = Logger()
    try:
        cmd = ["git", "-C", repo_path, "describe", "--tags", "--exact-match"]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        version = result.stdout.strip()
        logger.info(f"Extracted version {version} from {repo_path}")
        return version
    except subprocess.CalledProcessError:
        logger.info("No exact tag found, using default version")
        return "0.1.0"
