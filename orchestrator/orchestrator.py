#  Copyright Contributors to the Mainframe Software Hub for Linux Project.
#  SPDX-License-Identifier: Apache-2.0

import yaml
import importlib
import os
import shutil
import subprocess
import requests
import sys
from lib.github_api import GitHubRepo
from lib.versioning import get_version
from monitoring.logger import Logger
from builders.plugins.plugin_interface import ArtifactBuilder

class BuildOrchestrator:
    def __init__(self, config_path: str, selected_repos: list = None):
        self.logger = Logger()
        self.config = self._load_config(config_path)
        self.script_repo_paths = self._clone_scripts()
        self.builders = self._load_builders()
        self.processed_repos = set()
        self.selected_repos = set(selected_repos) if selected_repos else None

    def _load_config(self, config_path: str) -> dict:
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.error(f"Config file {config_path} not found")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"Failed to parse config file {config_path}: {e}")
            raise

    def _clone_scripts(self) -> dict:
        script_repos = self.config.get('script_repositories', [])
        script_repo_paths = {}
        for repo in script_repos:
            name = repo.get('name')
            url = repo.get('url')
            if not name or not url:
                self.logger.error(f"Invalid script repository configuration: {repo}")
                continue
            script_repo_path = f"/tmp/{name}"
            if not os.path.exists(script_repo_path):
                cmd = ["git", "clone", "--depth", "1", url, script_repo_path]
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    self.logger.info(f"Cloned script repo {url} to {script_repo_path}")
                    script_repo_paths[name] = script_repo_path
                except subprocess.CalledProcessError as e:
                    self.logger.error(f"Failed to clone script repo {url}: {e.stderr.decode()}")
                    raise
            else:
                self.logger.info(f"Script repo {name} already cloned at {script_repo_path}")
                script_repo_paths[name] = script_repo_path
        return script_repo_paths

    def _load_builders(self) -> dict:
        builders = {
            'script': 'builders.script.loz_script_builder.ScriptBuilder',
            'binary_go': 'builders.binary.go_binary_builder.GoBinaryBuilder'
        }
        loaded_builders = {}
        for key, module_path in builders.items():
            module_name, class_name = module_path.rsplit('.', 1)
            try:
                module = importlib.import_module(module_name)
                builder = getattr(module, class_name)()
                # Pass script_repo_paths to ScriptBuilder
                if key == 'script':
                    builder.set_script_repo_paths(self.script_repo_paths)
                loaded_builders[key] = getattr(module, class_name)()
            except ImportError as e:
                self.logger.error(f"Failed to load builder {key}: {e}")
        return loaded_builders

    def _get_repositories(self) -> list:
        org = self.config.get('organization')
        repos = []
        if self.config.get('scan_organization', False):
            token = os.getenv('GITHUB_TOKEN')
            if not token:
                self.logger.error("GITHUB_TOKEN not set for organization scanning")
                raise ValueError("GITHUB_TOKEN required")
            headers = {'Authorization': f'token {token}'}
            response = requests.get(f'https://api.github.com/orgs/{org}/repos', headers=headers)
            response.raise_for_status()
            repos = [{'name': repo['name'], 'url': repo['clone_url'], 'template': 'templates/loz-script-project.yaml'} for repo in response.json()]
        else:
            repos = self.config.get('repositories', [])

        # Filter repositories if specific ones are selected
        if self.selected_repos:
            repos = [repo for repo in repos if repo['name'] in self.selected_repos]
            if not repos:
                self.logger.error(f"No matching repositories found for {self.selected_repos}")
                raise ValueError(f"No matching repositories found for {self.selected_repos}")

        seen_names = set()
        unique_repos = []
        for repo in repos:
            if repo['name'] not in seen_names:
                unique_repos.append(repo)
                seen_names.add(repo['name'])
            else:
                self.logger.warning(f"Duplicate repository {repo['name']} ignored")
        
        self.logger.info(f"Found {len(unique_repos)} unique repositories: {[repo['name'] for repo in unique_repos]}")
        return unique_repos

    def _load_template(self, template_path: str, repo_name: str, global_schedule: str, global_webhook: bool) -> dict:
        try:
            with open(f"config/{template_path}", 'r') as f:
                template = yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.error(f"Template file config/{template_path} not found")
            raise
        for artifact in template.get('artifacts', []):
            if 'image_name' in artifact:
                artifact['image_name'] = artifact['image_name'].replace('{{repo_name}}', repo_name)
        template['schedule'] = template.get('schedule', global_schedule).replace('{{global_schedule}}', global_schedule)
        template['webhook'] = template.get('webhook', global_webhook)
        return template

    def _merge_config(self, template_config: dict, repo_path: str) -> dict:
        template_file = f"{repo_path}/.build-template.yaml"
        if os.path.exists(template_file):
            try:
                with open(template_file, 'r') as f:
                    repo_config = yaml.safe_load(f)
                template = self._load_template(repo_config['template'], os.path.basename(repo_path),
                                            template_config.get('schedule', '0 * * * *'),
                                            template_config.get('webhook', True))
                for artifact in repo_config.get('overrides', {}).get('artifacts', []):
                    for t_artifact in template['artifacts']:
                        if t_artifact['type'] == artifact['type']:
                            t_artifact.update(artifact)
                return template
            except (FileNotFoundError, yaml.YAMLError) as e:
                self.logger.error(f"Failed to load or parse {template_file}: {e}")
                raise
        return template_config

    def build_artifacts(self):
        repos = self._get_repositories()
        global_schedule = self.config.get('default_schedule', '0 * * * *')
        global_webhook = self.config.get('default_webhook', True)

        self.logger.info(f"Starting build process for {len(repos)} repositories")
        print(f"Starting build process for {len(repos)} repositories")
        for repo in repos:
            repo_name = repo['name']
            if repo_name in self.processed_repos:
                self.logger.warning(f"Skipping already processed repository {repo_name}")
                continue
            self.processed_repos.add(repo_name)
            repo_url = repo['url']
            repo_commit = repo['commit']
            template_path = repo.get('template', 'templates/loz-script-project.yaml')
            self.logger.info(f"Processing repository {repo_name}")

            repo_obj = GitHubRepo(repo_url)
            repo_path = repo_obj.clone(repo_commit)

            template_config = self._load_template(template_path, repo_name, global_schedule, global_webhook)
            config = self._merge_config(template_config, repo_path)

            for artifact in config.get('artifacts', []):
                artifact_type = artifact['type']
                builder_key = 'script' if 'build_script' in artifact else (f"binary_{artifact['language']}" if artifact_type == 'binary' else artifact_type)
                builder = self.builders.get(builder_key)
                build_script = artifact.get('build_script', {})
                if builder_key == 'script':
                    builder.set_script_repo_paths(self.script_repo_paths)
                if not builder:
                    self.logger.error(f"No builder for {builder_key} in repository {repo_name}")
                    continue
                try:
                    self.logger.info(f"Building artifact type {builder_key} for {repo_name}")
                    print(f"Building artifact type {builder_key} for project {repo_name}")
                    artifact_path = builder.build(repo_path, repo_name, artifact)
                    self.logger.info(f"Publishing artifact type {builder_key} for {repo_name}")
                    print(f"Publishing artifact type {builder_key} for project {repo_name}")
                    builder.publish(artifact_path, repo_name, artifact)
                    self.logger.info(f"Successfully built and published {builder_key} for {repo_name}")
                    print(f"Successfully built and published {builder_key} for project {repo_name}")
                    self.logger.info(f"Cleaning up temporary files")
                    shutil.rmtree(repo_path)
                except Exception as e:
                    self.logger.error(f"Failed to build/publish {builder_key} for project {repo_name}: {e}")
        self.logger.info("Build process completed")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 orchestrator/orchestrator.py <config_path> [repo_name1 repo_name2 ...]")
        sys.exit(1)
    
    config_path = sys.argv[1]
    selected_repos = sys.argv[2:] if len(sys.argv) > 2 else None
    try:
        print("Initiating build for project ", selected_repos)
        orchestrator = BuildOrchestrator(config_path, selected_repos)
        orchestrator.build_artifacts()
        print("Build completed for project ", selected_repos)
    except Exception as e:
        print(f"Error running orchestrator: {e}")
        sys.exit(1)
