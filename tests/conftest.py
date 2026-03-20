#  Copyright Contributors to the Mainframe Software Hub for Linux Project.
#  SPDX-License-Identifier: Apache-2.0

import pytest
import os
import tempfile
import shutil


@pytest.fixture
def temp_repo_dir():
    """Create a temporary directory for repository simulation."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_subprocess_run(mocker):
    """Mock subprocess.run to avoid actual command execution."""
    return mocker.patch('subprocess.run')


@pytest.fixture
def mock_os_listdir(mocker):
    """Mock os.listdir for directory content simulation."""
    return mocker.patch('os.listdir')


@pytest.fixture
def mock_os_path_exists(mocker):
    """Mock os.path.exists for file existence simulation."""
    return mocker.patch('os.path.exists')


@pytest.fixture
def sample_artifact():
    """Sample artifact configuration for testing."""
    return {
        "version": "1.0.0",
        "type": "binary"
    }
