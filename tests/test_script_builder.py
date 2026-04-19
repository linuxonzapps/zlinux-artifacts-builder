import pytest
import os
from unittest.mock import patch, MagicMock
from builders.script.loz_script_builder import ScriptBuilder


class TestScriptBuilder:
    """Test ScriptBuilder build and publish methods."""

    def test_build_success(self, temp_repo_dir, mocker):
        """Test successful script-based build."""
        # Setup script repository
        script_repo_path = os.path.join(temp_repo_dir, "scripts")
        os.makedirs(script_repo_path, exist_ok=True)
        
        script_path = os.path.join(temp_repo_dir, "build.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\necho 'Building...'")
        
        # Create expected output file
        output_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.tar.gz")
        with open(output_path, "w") as f:
            f.write("fake tarball")
        
        # Mock subprocess.run
        mock_run = mocker.patch('subprocess.run')
        
        # Build
        builder = ScriptBuilder()
        builder.set_script_repo_paths({"linux-on-ibm-z-scripts": script_repo_path})
        
        artifact = {
            "version": "1.0.0",
            "build_script": {
                "repo_name": "linux-on-ibm-z-scripts",
                "path": "build.sh",
                "args": "--platform s390x"
            }
        }
        result_path = builder.build(temp_repo_dir, "test-app", artifact)
        
        # Assertions
        assert os.path.normpath(result_path) == os.path.normpath(output_path)
        mock_run.assert_called_once()
        
        # Verify Docker command
        docker_call = mock_run.call_args
        assert "docker" in docker_call[0][0]
        assert "run" in docker_call[0][0]
        assert "bash" in docker_call[0][0]

    def test_build_with_docker_required(self, temp_repo_dir, mocker):
        """Test build when Docker is required within container."""
        script_repo_path = os.path.join(temp_repo_dir, "scripts")
        os.makedirs(script_repo_path, exist_ok=True)
        
        script_path = os.path.join(temp_repo_dir, "build.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\necho 'Building with Docker...'")
        
        output_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.tar.gz")
        with open(output_path, "w") as f:
            f.write("fake tarball")
        
        # Set environment variables
        mocker.patch.dict(os.environ, {
            'DOCKER_USERNAME': 'testuser',
            'DOCKER_PASSWORD': 'testpass',
            'GH_TOKEN': 'ghtoken',
            'GH_PUSH_USER': 'pushuser'
        })
        
        mock_run = mocker.patch('subprocess.run')
        
        builder = ScriptBuilder()
        builder.set_script_repo_paths({"linux-on-ibm-z-scripts": script_repo_path})
        
        artifact = {
            "version": "1.0.0",
            "build_script": {
                "repo_name": "linux-on-ibm-z-scripts",
                "path": "build.sh",
                "docker_required": True
            }
        }
        builder.build(temp_repo_dir, "test-app", artifact)
        
        # Verify Docker socket is mounted
        docker_call = mock_run.call_args
        assert "/var/run/docker.sock:/var/run/docker.sock" in docker_call[0][0]
        assert "-e" in docker_call[0][0]

    def test_build_missing_script_path(self, temp_repo_dir):
        """Test build fails when script path is not specified."""
        builder = ScriptBuilder()
        artifact = {
            "version": "1.0.0",
            "build_script": {
                "repo_name": "linux-on-ibm-z-scripts"
                # Missing path
            }
        }
        
        with pytest.raises(ValueError, match="build_script.path required"):
            builder.build(temp_repo_dir, "test-app", artifact)

    def test_build_script_repo_not_found(self, temp_repo_dir):
        """Test build fails when script repository is not found."""
        builder = ScriptBuilder()
        # Don't set script_repo_paths
        
        artifact = {
            "version": "1.0.0",
            "build_script": {
                "repo_name": "missing-repo",
                "path": "build.sh"
            }
        }
        
        with pytest.raises(ValueError, match="Script repository missing-repo not found"):
            builder.build(temp_repo_dir, "test-app", artifact)

    def test_build_script_file_not_found(self, temp_repo_dir):
        """Test build fails when script file doesn't exist."""
        script_repo_path = os.path.join(temp_repo_dir, "scripts")
        os.makedirs(script_repo_path, exist_ok=True)
        
        builder = ScriptBuilder()
        builder.set_script_repo_paths({"linux-on-ibm-z-scripts": script_repo_path})
        
        artifact = {
            "version": "1.0.0",
            "build_script": {
                "repo_name": "linux-on-ibm-z-scripts",
                "path": "nonexistent.sh"
            }
        }
        
        with pytest.raises(FileNotFoundError, match="Script .* not found"):
            builder.build(temp_repo_dir, "test-app", artifact)

    def test_build_output_not_created(self, temp_repo_dir, mocker):
        """Test build fails when expected output is not created."""
        script_repo_path = os.path.join(temp_repo_dir, "scripts")
        os.makedirs(script_repo_path, exist_ok=True)
        
        script_path = os.path.join(temp_repo_dir, "build.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\necho 'Building...'")
        
        # Don't create output file
        mock_run = mocker.patch('subprocess.run')
        
        builder = ScriptBuilder()
        builder.set_script_repo_paths({"linux-on-ibm-z-scripts": script_repo_path})
        
        artifact = {
            "version": "1.0.0",
            "build_script": {
                "repo_name": "linux-on-ibm-z-scripts",
                "path": "build.sh"
            }
        }
        
        with pytest.raises(FileNotFoundError, match="Expected output .* not found"):
            builder.build(temp_repo_dir, "test-app", artifact)

    def test_build_subprocess_error(self, temp_repo_dir, mocker):
        """Test build handles subprocess errors gracefully."""
        script_repo_path = os.path.join(temp_repo_dir, "scripts")
        os.makedirs(script_repo_path, exist_ok=True)
        
        script_path = os.path.join(temp_repo_dir, "build.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\nexit 1")
        
        import subprocess
        mock_run = mocker.patch('subprocess.run', side_effect=subprocess.CalledProcessError(
            1, 'bash', stderr=b'Script error'
        ))
        
        builder = ScriptBuilder()
        builder.set_script_repo_paths({"linux-on-ibm-z-scripts": script_repo_path})
        
        artifact = {
            "version": "1.0.0",
            "build_script": {
                "repo_name": "linux-on-ibm-z-scripts",
                "path": "build.sh"
            }
        }
        
        with pytest.raises(subprocess.CalledProcessError):
            builder.build(temp_repo_dir, "test-app", artifact)

    def test_build_custom_docker_image(self, temp_repo_dir, mocker):
        """Test build with custom Docker image."""
        script_repo_path = os.path.join(temp_repo_dir, "scripts")
        os.makedirs(script_repo_path, exist_ok=True)
        
        script_path = os.path.join(temp_repo_dir, "build.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\necho 'Building...'")
        
        output_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.tar.gz")
        with open(output_path, "w") as f:
            f.write("fake tarball")
        
        mock_run = mocker.patch('subprocess.run')
        
        builder = ScriptBuilder()
        builder.set_script_repo_paths({"linux-on-ibm-z-scripts": script_repo_path})
        
        artifact = {
            "version": "1.0.0",
            "build_script": {
                "repo_name": "linux-on-ibm-z-scripts",
                "path": "build.sh",
                "docker_image": "alpine:latest"
            }
        }
        builder.build(temp_repo_dir, "test-app", artifact)
        
        # Verify custom Docker image
        docker_call = mock_run.call_args
        assert "alpine:latest" in docker_call[0][0]

    @patch('lib.checksum.generate_checksum')
    def test_publish_success(self, mock_checksum, temp_repo_dir, mocker):
        """Test successful artifact publishing."""
        artifact_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.tar.gz")
        with open(artifact_path, "w") as f:
            f.write("fake tarball")
        
        mock_checksum.return_value = "abc123"
        mock_run = mocker.patch('subprocess.run')
        
        builder = ScriptBuilder()
        artifact = {"version": "1.0.0"}
        builder.publish(artifact_path, "test-app", artifact)
        
        # Assertions
        mock_checksum.assert_called_once_with(artifact_path)
        mock_run.assert_called_once()
        
        # Verify gh release create command
        gh_call = mock_run.call_args
        assert "gh" in gh_call[0][0]
        assert "release" in gh_call[0][0]
        assert "create" in gh_call[0][0]
        assert "v1.0.0" in gh_call[0][0]

    @patch('lib.checksum.generate_checksum')
    def test_publish_with_rpm(self, mock_checksum, temp_repo_dir, mocker):
        """Test publishing with additional RPM artifact."""
        artifact_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.tar.gz")
        rpm_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.rpm")
        
        with open(artifact_path, "w") as f:
            f.write("fake tarball")
        with open(rpm_path, "w") as f:
            f.write("fake rpm")
        
        mock_checksum.return_value = "abc123"
        mock_run = mocker.patch('subprocess.run')
        
        builder = ScriptBuilder()
        artifact = {"version": "1.0.0"}
        builder.publish(artifact_path, "test-app", artifact)
        
        # Should call gh release twice: create + upload
        assert mock_run.call_count == 2
        
        # Verify upload call
        upload_call = mock_run.call_args_list[1]
        assert "upload" in upload_call[0][0]
        # Normalize paths for cross-platform comparison
        uploaded_file = os.path.normpath(upload_call[0][0][-1])
        assert os.path.normpath(rpm_path) == uploaded_file

    @patch('lib.checksum.generate_checksum')
    def test_publish_with_deb(self, mock_checksum, temp_repo_dir, mocker):
        """Test publishing with additional DEB artifact."""
        artifact_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.tar.gz")
        deb_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.deb")
        
        with open(artifact_path, "w") as f:
            f.write("fake tarball")
        with open(deb_path, "w") as f:
            f.write("fake deb")
        
        mock_checksum.return_value = "abc123"
        mock_run = mocker.patch('subprocess.run')
        
        builder = ScriptBuilder()
        artifact = {"version": "1.0.0"}
        builder.publish(artifact_path, "test-app", artifact)
        
        # Should call gh release twice: create + upload
        assert mock_run.call_count == 2
        
        # Verify upload call
        upload_call = mock_run.call_args_list[1]
        assert "upload" in upload_call[0][0]
        # Normalize paths for cross-platform comparison
        uploaded_file = os.path.normpath(upload_call[0][0][-1])
        assert os.path.normpath(deb_path) == uploaded_file

    @patch('lib.checksum.generate_checksum')
    def test_publish_with_distro_marker_renames_tarball(self, mock_checksum, temp_repo_dir, mocker):
        """When .distro_zab.txt is present, the tarball is renamed with distro suffix before publishing."""
        artifact_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.tar.gz")
        sha256_path = f"{artifact_path}.sha256"
        with open(artifact_path, "w") as f:
            f.write("fake tarball")
        with open(sha256_path, "w") as f:
            f.write("abc123")
        with open(os.path.join(temp_repo_dir, ".distro_zab.txt"), "w") as f:
            f.write("ubuntu-22.04\n")

        mock_checksum.return_value = "abc123"
        mock_run = mocker.patch('subprocess.run')

        builder = ScriptBuilder()
        builder.publish(artifact_path, "test-app", {"version": "1.0.0"})

        renamed_tarball = os.path.join(
            temp_repo_dir, "test-app-1.0.0-ubuntu-22.04-linux-s390x.tar.gz"
        )
        assert os.path.exists(renamed_tarball)
        assert os.path.exists(f"{renamed_tarball}.sha256")
        assert not os.path.exists(artifact_path)

        mock_run.assert_called_once()
        create_call_args = mock_run.call_args[0][0]
        assert renamed_tarball in create_call_args
        assert f"{renamed_tarball}.sha256" in create_call_args

    @patch('lib.checksum.generate_checksum')
    def test_publish_with_distro_marker_renames_rpm_and_deb(self, mock_checksum, temp_repo_dir, mocker):
        """RPM and DEB companion artifacts also get renamed with the distro suffix when the marker is present."""
        artifact_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.tar.gz")
        rpm_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.rpm")
        deb_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.deb")
        with open(artifact_path, "w") as f:
            f.write("fake tarball")
        with open(f"{artifact_path}.sha256", "w") as f:
            f.write("abc123")
        with open(rpm_path, "w") as f:
            f.write("fake rpm")
        with open(deb_path, "w") as f:
            f.write("fake deb")
        with open(os.path.join(temp_repo_dir, ".distro_zab.txt"), "w") as f:
            f.write("ubuntu-22.04")

        mock_checksum.return_value = "abc123"
        mock_run = mocker.patch('subprocess.run')

        builder = ScriptBuilder()
        builder.publish(artifact_path, "test-app", {"version": "1.0.0"})

        expected_rpm = os.path.join(
            temp_repo_dir, "test-app-1.0.0-ubuntu-22.04-linux-s390x.rpm"
        )
        expected_deb = os.path.join(
            temp_repo_dir, "test-app-1.0.0-ubuntu-22.04-linux-s390x.deb"
        )
        assert os.path.exists(expected_rpm)
        assert os.path.exists(expected_deb)
        assert not os.path.exists(rpm_path)
        assert not os.path.exists(deb_path)

        assert mock_run.call_count == 3
        rpm_upload_args = mock_run.call_args_list[1][0][0]
        deb_upload_args = mock_run.call_args_list[2][0][0]
        assert "upload" in rpm_upload_args
        assert os.path.normpath(rpm_upload_args[-1]) == os.path.normpath(expected_rpm)
        assert "upload" in deb_upload_args
        assert os.path.normpath(deb_upload_args[-1]) == os.path.normpath(expected_deb)

    @patch('lib.checksum.generate_checksum')
    def test_publish_empty_distro_marker_falls_back_to_plain_names(self, mock_checksum, temp_repo_dir, mocker):
        """An empty .distro_zab.txt should NOT apply any distro suffix."""
        artifact_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.tar.gz")
        rpm_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.rpm")
        with open(artifact_path, "w") as f:
            f.write("fake tarball")
        with open(rpm_path, "w") as f:
            f.write("fake rpm")
        with open(os.path.join(temp_repo_dir, ".distro_zab.txt"), "w") as f:
            f.write("")

        mock_checksum.return_value = "abc123"
        mock_run = mocker.patch('subprocess.run')

        builder = ScriptBuilder()
        builder.publish(artifact_path, "test-app", {"version": "1.0.0"})

        assert os.path.exists(artifact_path)
        assert os.path.exists(rpm_path)

        assert mock_run.call_count == 2
        rpm_upload_args = mock_run.call_args_list[1][0][0]
        assert os.path.normpath(rpm_upload_args[-1]) == os.path.normpath(rpm_path)

    @patch('lib.checksum.generate_checksum')
    def test_publish_subprocess_error(self, mock_checksum, temp_repo_dir, mocker):
        """Test publish handles subprocess errors gracefully."""
        artifact_path = os.path.join(temp_repo_dir, "test-app-1.0.0-linux-s390x.tar.gz")
        with open(artifact_path, "w") as f:
            f.write("fake tarball")
        
        mock_checksum.return_value = "abc123"
        
        import subprocess
        mock_run = mocker.patch('subprocess.run', side_effect=subprocess.CalledProcessError(
            1, 'gh', stderr=b'GitHub error'
        ))
        
        builder = ScriptBuilder()
        artifact = {"version": "1.0.0"}
        
        # Note: The actual code doesn't have error handling for publish in ScriptBuilder
        # This test documents that behavior
        with pytest.raises(subprocess.CalledProcessError):
            builder.publish(artifact_path, "test-app", artifact)
