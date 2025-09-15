#  Copyright Contributors to the Mainframe Software Hub for Linux Project.
#  SPDX-License-Identifier: Apache-2.0

import hashlib
import os
from monitoring.logger import Logger

def generate_checksum(file_path: str) -> str:
    """Generate SHA256 checksum for a file and save it to <file_path>.sha256.

    Args:
        file_path (str): Path to the file to checksum.

    Returns:
        str: The SHA256 checksum as a hexadecimal string.

    Raises:
        FileNotFoundError: If the input file does not exist.
        IOError: If there is an error reading the file or writing the checksum.
    """
    logger = Logger()
    try:
        if not os.path.exists(file_path):
            logger.error(f"File {file_path} does not exist")
            raise FileNotFoundError(f"File {file_path} does not exist")
        
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        checksum = sha256_hash.hexdigest()
        checksum_file = f"{file_path}.sha256"
        
        with open(checksum_file, "w") as f:
            f.write(checksum)
        
        logger.info(f"Generated checksum for {file_path}: {checksum}")
        return checksum
    
    except (FileNotFoundError, IOError) as e:
        logger.error(f"Failed to generate checksum for {file_path}: {e}")
        raise
