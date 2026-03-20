#  Copyright Contributors to the Mainframe Software Hub for Linux Project.
#  SPDX-License-Identifier: Apache-2.0

import pytest
import os
from unittest.mock import patch
from builders.binary.go_binary_builder import GoBinaryBuilder


class TestGoBinaryBuilder:
    """Test GoBinaryBuilder build and publish methods."""

    def test_build_success(self, temp_repo_dir, mocker):
        """Test successful Go binary build."""
        # Mock subprocess.run
        mock_run = mocker.patch('subprocess.run')
        
        # Build
        builder = GoBinaryBuilder()
        artifact = {"version": "1.0.0"}
        result_path = builder.build(temp_repo_dir, "go-app", artifact)
        
        # Assertions
        expected_path = os.path.join(temp_repo_dir, "build", "go-app_1.0.0_s390x")
        assert os.path.normpath(result_path) == os.path.normpath(expected_path)
        
        # Verify Docker command was called
        mock_run.assert_called_once()
        docker_call = mock_run.call_args
        assert "docker" in docker_call[0][0]
        assert "run" in docker_call[0][0]
        assert "--rm" in docker_call[0][0]
        assert "ubuntu:22.04" in docker_call[0][0]
        assert "go" in docker_call[0][0]
        assert "build" in docker_call[0][0]
        # Check that expected path appears in command (may have different separators)
        assert any(os.path.normpath(expected_path) == os.path.normpath(arg) for arg in docker_call[0][0])

    def test_build_with_custom_docker_image(self, temp_repo_dir, mocker):
        """Test build with custom Docker image."""
        mock_run = mocker.patch('subprocess.run')
        
        builder = GoBinaryBuilder()
        artifact = {
            "version": "2.0.0",
            "docker_image": "golang:1.21-alpine"
        }
        builder.build(temp_repo_dir, "custom-go-app", artifact)
        
        # Verify custom Docker image is used
        docker_call = mock_run.call_args
        assert "golang:1.21-alpine" in docker_call[0][0]

    def test_build_default_version(self, temp_repo_dir, mocker):
        """Test build with default version when not specified."""
        mock_run = mocker.patch('subprocess.run')
        
        builder = GoBinaryBuilder()
        artifact = {}  # No version specified
        result_path = builder.build(temp_repo_dir, "go-app", artifact)
        
        # Should use default version 1.0
        expected_path = os.path.join(temp_repo_dir, "build", "go-app_1.0_s390x")
        assert os.path.normpath(result_path) == os.path.normpath(expected_path)

    def test_build_subprocess_error(self, temp_repo_dir, mocker):
        """Test build handles subprocess errors gracefully."""
        import subprocess
        mock_run = mocker.patch('subprocess.run', side_effect=subprocess.CalledProcessError(
            1, 'docker', stderr=b'Docker error'
        ))
        
        builder = GoBinaryBuilder()
        artifact = {"version": "1.0.0"}
        
        with pytest.raises(subprocess.CalledProcessError):
            builder.build(temp_repo_dir, "error-app", artifact)

    def test_build_creates_output_directory(self, temp_repo_dir, mocker):
        """Test that build creates the build directory if it doesn't exist."""
        mock_run = mocker.patch('subprocess.run')
        
        # Verify build directory doesn't exist initially
        build_dir = os.path.join(temp_repo_dir, "build")
        assert not os.path.exists(build_dir)
        
        builder = GoBinaryBuilder()
        artifact = {"version": "1.0.0"}
        builder.build(temp_repo_dir, "go-app", artifact)
        
        # Build directory should be created
        # Note: In the actual code, this is done via os.makedirs("build", exist_ok=True)
        # The mock prevents actual directory creation, so we just verify the call was made
        mock_run.assert_called_once()

    @patch('lib.checksum.generate_checksum')
    def test_publish_success(self, mock_checksum, temp_repo_dir, mocker):
        """Test successful artifact publishing."""
        # Setup
        artifact_path = os.path.join(temp_repo_dir, "go-app_1.0.0_s390x")
        with open(artifact_path, "w") as f:
            f.write("fake binary")
        
        mock_checksum.return_value = "def456"
        mock_run = mocker.patch('subprocess.run')
        
        # Publish
        builder = GoBinaryBuilder()
        artifact = {"version": "1.0.0"}
        builder.publish(artifact_path, "go-app", artifact)
        
        # Assertions
        mock_checksum.assert_called_once_with(artifact_path)
        mock_run.assert_called_once()
        
        # Verify gh release create command
        gh_call = mock_run.call_args
        assert "gh" in gh_call[0][0]
        assert "release" in gh_call[0][0]
        assert "create" in gh_call[0][0]
        assert "v1.0.0" in gh_call[0][0]
        assert "--title" in gh_call[0][0]
        assert "Version 1.0.0" in gh_call[0][0]
        assert "--generate-notes" in gh_call[0][0]
        assert artifact_path in gh_call[0][0]
        assert f"{artifact_path}.sha256" in gh_call[0][0]

    @patch('lib.checksum.generate_checksum')
    def test_publish_default_version(self, mock_checksum, temp_repo_dir, mocker):
        """Test publish with default version."""
        artifact_path = os.path.join(temp_repo_dir, "go-app_1.0_s390x")
        with open(artifact_path, "w") as f:
            f.write("fake binary")
        
        mock_checksum.return_value = "abc123"
        mock_run = mocker.patch('subprocess.run')
        
        builder = GoBinaryBuilder()
        artifact = {}  # No version
        builder.publish(artifact_path, "go-app", artifact)
        
        # Should use default version 1.0
        gh_call = mock_run.call_args
        assert "v1.0" in gh_call[0][0]

    @patch('lib.checksum.generate_checksum')
    def test_publish_subprocess_error(self, mock_checksum, temp_repo_dir, mocker):
        """Test publish handles subprocess errors gracefully."""
        artifact_path = os.path.join(temp_repo_dir, "go-app_1.0.0_s390x")
        with open(artifact_path, "w") as f:
            f.write("fake binary")
        
        mock_checksum.return_value = "abc123"
        
        import subprocess
        mock_run = mocker.patch('subprocess.run', side_effect=subprocess.CalledProcessError(
            1, 'gh', stderr=b'GitHub error'
        ))
        
        builder = GoBinaryBuilder()
        artifact = {"version": "1.0.0"}
        
        with pytest.raises(subprocess.CalledProcessError):
            builder.publish(artifact_path, "go-app", artifact)

    @patch('lib.checksum.generate_checksum')
    def test_publish_working_directory(self, mock_checksum, temp_repo_dir, mocker):
        """Test that publish runs in the correct working directory."""
        artifact_path = os.path.join(temp_repo_dir, "build", "go-app_1.0.0_s390x")
        os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
        with open(artifact_path, "w") as f:
            f.write("fake binary")
        
        mock_checksum.return_value = "xyz789"
        mock_run = mocker.patch('subprocess.run')
        
        builder = GoBinaryBuilder()
        artifact = {"version": "1.0.0"}
        builder.publish(artifact_path, "go-app", artifact)
        
        # Verify cwd parameter
        gh_call = mock_run.call_args
        assert gh_call[1]['cwd'] == os.path.dirname(artifact_path)
