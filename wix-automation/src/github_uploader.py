import os
import json
import base64
import logging
from datetime import datetime
from github import Github
from pathlib import Path

class GitHubUploader:
    def __init__(self, repo_name, organization=None):
        self.github = Github(os.getenv('GITHUB_TOKEN'))
        self.repo_name = repo_name
        self.organization = organization
        self.repo = self._get_repository()
        self._setup_logging()
    
    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _get_repository(self):
        try:
            if self.organization:
                return self.github.get_organization(self.organization).get_repo(self.repo_name)
            else:
                return self.github.get_user().get_repo(self.repo_name)
        except Exception as e:
            self.logger.error(f"Failed to access repository: {e}")
            raise
    
    def upload_file(self, local_path, repo_path, commit_message=None):
        try:
            with open(local_path, 'r') as f:
                content = f.read()
            
            if commit_message is None:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                commit_message = f"Automated upload of Wix traffic data - {timestamp}"
            
            try:
                existing_file = self.repo.get_contents(repo_path)
                self.repo.update_file(
                    repo_path,
                    commit_message,
                    content,
                    existing_file.sha
                )
                self.logger.info(f"Updated existing file: {repo_path}")
            except:
                self.repo.create_file(
                    repo_path,
                    commit_message,
                    content
                )
                self.logger.info(f"Created new file: {repo_path}")
            
            return self._generate_raw_url(repo_path)
            
        except Exception as e:
            self.logger.error(f"Failed to upload file {local_path}: {e}")
            raise
    
    def _generate_raw_url(self, repo_path):
        if self.organization:
            base_url = f"https://raw.githubusercontent.com/{self.organization}/{self.repo_name}"
        else:
            username = self.github.get_user().login
            base_url = f"https://raw.githubusercontent.com/{username}/{self.repo_name}"
        
        return f"{base_url}/main/{repo_path}"
    
    def batch_upload(self, file_mappings):
        uploaded_urls = []
        
        for local_path, repo_path in file_mappings.items():
            try:
                url = self.upload_file(local_path, repo_path)
                uploaded_urls.append({
                    'local_path': local_path,
                    'repo_path': repo_path,
                    'raw_url': url,
                    'upload_time': datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"Failed to upload {local_path}: {e}")
        
        return uploaded_urls
    
    def create_summary_file(self, uploaded_files, summary_path="data/upload_summary.json"):
        summary = {
            'upload_session': datetime.now().isoformat(),
            'total_files': len(uploaded_files),
            'files': uploaded_files,
            'repository': f"{self.organization}/{self.repo_name}" if self.organization else self.repo_name
        }
        
        try:
            summary_content = json.dumps(summary, indent=2)
            self.repo.create_file(
                summary_path,
                f"Upload summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                summary_content
            )
            
            return self._generate_raw_url(summary_path)
            
        except Exception as e:
            self.logger.error(f"Failed to create summary file: {e}")
            return None