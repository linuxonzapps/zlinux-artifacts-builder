import pytest
import os
from unittest.mock import MagicMock, call, patch
from builders.binary.java_binary_builder import JavaBinaryBuilder, detect_build_system, BUILD_SYSTEMS


class TestDetectBuildSystem:
    """Test build system detection for Maven and Gradle."""

    def test_detect_maven(self, temp_repo_dir):
        """Test detection of Maven build system."""
        pom_path = os.path.join(temp_repo_dir, "pom.xml")
        with open(pom_path, "w") as f:
            f.write("<project></project>")
        
        system, config = detect_build_system(temp_repo_dir)
        
        assert system == "maven"
        assert config == BUILD_SYSTEMS["maven"]

    def test_detect_gradle_groovy(self, temp_repo_dir):
        """Test detection of Gradle (Groovy) build system."""
        gradle_path = os.path.join(temp_repo_dir, "build.gradle")
        with open(gradle_path, "w") as f:
            f.write("plugins { id 'java' }")
        
        system, config = detect_build_system(temp_repo_dir)
        
        assert system == "gradle"
        assert config == BUILD_SYSTEMS["gradle"]

    def test_detect_gradle_kotlin(self, temp_repo_dir):
        """Test detection of Gradle (Kotlin) build system."""
        gradle_kts_path = os.path.join(temp_repo_dir, "build.gradle.kts")
        with open(gradle_kts_path, "w") as f:
            f.write("plugins { kotlin(\"jvm\") }")
        
        system, config = detect_build_system(temp_repo_dir)
        
        assert system == "gradle"
        assert config == BUILD_SYSTEMS["gradle"]

    def test_no_build_system_found(self, temp_repo_dir):
        """Test when no build system is detected."""
        system, config = detect_build_system(temp_repo_dir)
        
        assert system is None
        assert config is None


class TestJavaBinaryBuilder:
    """Test JavaBinaryBuilder build and publish methods."""

    def test_build_maven_success(self, temp_repo_dir, mocker):
        """Test successful Maven build."""
        # Setup
        pom_path = os.path.join(temp_repo_dir, "pom.xml")
        with open(pom_path, "w") as f:
            f.write("<project></project>")
        
        target_dir = os.path.join(temp_repo_dir, "target")
        os.makedirs(target_dir, exist_ok=True)
        
        jar_file = os.path.join(target_dir, "app-1.0.0.jar")
        with open(jar_file, "w") as f:
            f.write("fake jar content")
        
        # Mock subprocess.run
        mock_run = mocker.patch('subprocess.run')
        
        # Mock os.listdir to return JAR files
        mocker.patch('os.listdir', return_value=["app-1.0.0.jar"])
        
        # Build
        builder = JavaBinaryBuilder()
        artifact = {"version": "1.0.0"}
        result_path = builder.build(temp_repo_dir, "test-app", artifact)
        
        # Assertions
        assert result_path == os.path.join(temp_repo_dir, "build", "test-app_1.0.0_s390x.jar")
        assert mock_run.call_count == 2  # docker run + cp
        
        # Verify Docker command
        docker_call = mock_run.call_args_list[0]
        assert "docker" in docker_call[0][0]
        assert "run" in docker_call[0][0]
        assert "maven:3.9-eclipse-temurin-17" in docker_call[0][0]
        assert "mvn" in docker_call[0][0]
        assert "-DskipTests" in docker_call[0][0]

    def test_build_gradle_success(self, temp_repo_dir, mocker):
        """Test successful Gradle build."""
        # Setup
        gradle_path = os.path.join(temp_repo_dir, "build.gradle")
        with open(gradle_path, "w") as f:
            f.write("plugins { id 'java' }")
        
        build_dir = os.path.join(temp_repo_dir, "build", "libs")
        os.makedirs(build_dir, exist_ok=True)
        
        jar_file = os.path.join(build_dir, "app-1.0.0.jar")
        with open(jar_file, "w") as f:
            f.write("fake jar content")
        
        # Mock subprocess.run
        mock_run = mocker.patch('subprocess.run')
        
        # Mock os.listdir
        mocker.patch('os.listdir', return_value=["app-1.0.0.jar"])
        
        # Build
        builder = JavaBinaryBuilder()
        artifact = {"version": "2.0.0"}
        result_path = builder.build(temp_repo_dir, "gradle-app", artifact)
        
        # Assertions
        assert result_path == os.path.join(temp_repo_dir, "build", "gradle-app_2.0.0_s390x.jar")
        assert mock_run.call_count == 2
        
        # Verify Docker command uses Gradle
        docker_call = mock_run.call_args_list[0]
        assert "gradle:8.7-jdk17" in docker_call[0][0]
        assert "gradle" in docker_call[0][0]

    def test_build_custom_docker_image(self, temp_repo_dir, mocker):
        """Test build with custom Docker image."""
        # Setup
        pom_path = os.path.join(temp_repo_dir, "pom.xml")
        with open(pom_path, "w") as f:
            f.write("<project></project>")
        
        target_dir = os.path.join(temp_repo_dir, "target")
        os.makedirs(target_dir, exist_ok=True)
        jar_file = os.path.join(target_dir, "app.jar")
        with open(jar_file, "w") as f:
            f.write("fake jar")
        
        mock_run = mocker.patch('subprocess.run')
        mocker.patch('os.listdir', return_value=["app.jar"])
        
        # Build with custom image
        builder = JavaBinaryBuilder()
        artifact = {
            "version": "1.0.0",
            "docker_image": "maven:3.9-eclipse-temurin-21"
        }
        builder.build(temp_repo_dir, "custom-app", artifact)
        
        # Verify custom Docker image is used
        docker_call = mock_run.call_args_list[0]
        assert "maven:3.9-eclipse-temurin-21" in docker_call[0][0]

    def test_build_no_build_system_found(self, temp_repo_dir):
        """Test build fails when no build system is found."""
        builder = JavaBinaryBuilder()
        artifact = {"version": "1.0.0"}
        
        with pytest.raises(RuntimeError, match="No supported Java build file found"):
            builder.build(temp_repo_dir, "no-build", artifact)

    def test_build_no_jar_found(self, temp_repo_dir, mocker):
        """Test build fails when no JAR file is produced."""
        # Setup Maven project without JAR output
        pom_path = os.path.join(temp_repo_dir, "pom.xml")
        with open(pom_path, "w") as f:
            f.write("<project></project>")
        
        target_dir = os.path.join(temp_repo_dir, "target")
        os.makedirs(target_dir, exist_ok=True)
        
        mock_run = mocker.patch('subprocess.run')
        mocker.patch('os.listdir', return_value=[])  # No JARs
        
        builder = JavaBinaryBuilder()
        artifact = {"version": "1.0.0"}
        
        with pytest.raises(RuntimeError, match="No runnable JAR found"):
            builder.build(temp_repo_dir, "no-jar", artifact)

    def test_build_filters_sources_and_javadoc_jars(self, temp_repo_dir, mocker):
        """Test that sources and javadoc JARs are filtered out."""
        pom_path = os.path.join(temp_repo_dir, "pom.xml")
        with open(pom_path, "w") as f:
            f.write("<project></project>")
        
        target_dir = os.path.join(temp_repo_dir, "target")
        os.makedirs(target_dir, exist_ok=True)
        
        # Create multiple JARs
        for jar_name in ["app-1.0.0.jar", "app-1.0.0-sources.jar", "app-1.0.0-javadoc.jar"]:
            with open(os.path.join(target_dir, jar_name), "w") as f:
                f.write("fake jar")
        
        mock_run = mocker.patch('subprocess.run')
        mocker.patch('os.listdir', return_value=[
            "app-1.0.0.jar", 
            "app-1.0.0-sources.jar", 
            "app-1.0.0-javadoc.jar"
        ])
        
        builder = JavaBinaryBuilder()
        artifact = {"version": "1.0.0"}
        builder.build(temp_repo_dir, "multi-jar", artifact)
        
        # Verify cp command uses main JAR, not sources/javadoc
        cp_call = mock_run.call_args_list[1]
        assert "app-1.0.0.jar" in cp_call[0][0][1]
        assert "sources" not in cp_call[0][0][1]
        assert "javadoc" not in cp_call[0][0][1]

    def test_build_subprocess_error(self, temp_repo_dir, mocker):
        """Test build handles subprocess errors gracefully."""
        pom_path = os.path.join(temp_repo_dir, "pom.xml")
        with open(pom_path, "w") as f:
            f.write("<project></project>")
        
        # Mock subprocess to raise error
        import subprocess
        mock_run = mocker.patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'docker'))
        
        builder = JavaBinaryBuilder()
        artifact = {"version": "1.0.0"}
        
        with pytest.raises(subprocess.CalledProcessError):
            builder.build(temp_repo_dir, "error-app", artifact)

    @patch('lib.checksum.generate_checksum')
    def test_publish_success(self, mock_checksum, temp_repo_dir, mocker):
        """Test successful artifact publishing."""
        # Setup
        artifact_path = os.path.join(temp_repo_dir, "test-app_1.0.0_s390x.jar")
        with open(artifact_path, "w") as f:
            f.write("fake jar")
        
        mock_checksum.return_value = "abc123"
        mock_run = mocker.patch('subprocess.run')
        
        # Publish
        builder = JavaBinaryBuilder()
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
    def test_publish_subprocess_error(self, mock_checksum, temp_repo_dir, mocker):
        """Test publish handles errors gracefully."""
        artifact_path = os.path.join(temp_repo_dir, "test-app_1.0.0_s390x.jar")
        with open(artifact_path, "w") as f:
            f.write("fake jar")
        
        mock_checksum.return_value = "abc123"
        
        # Mock subprocess to raise error
        import subprocess
        mock_run = mocker.patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'gh'))
        
        builder = JavaBinaryBuilder()
        artifact = {"version": "1.0.0"}
        
        with pytest.raises(subprocess.CalledProcessError):
            builder.publish(artifact_path, "test-app", artifact)
