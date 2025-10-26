import ast
import base64
import os
from typing import Dict, List
import logging
from github import Github
from github.ContentFile import ContentFile

class CodeAnalyzer:
    """
    Analyzes Python source files in a repository to extract docstrings and comments.
    """
    
    def __init__(self, github_token: str, repo_owner: str, repo_name: str):
        """Initialize CodeAnalyzer with GitHub credentials and repo info.
        
        Args:
            github_token: GitHub access token
            repo_owner: Repository owner/username
            repo_name: Repository name
        """
        self.github = Github(github_token)
        self.repo = self.github.get_repo(f"{repo_owner}/{repo_name}")

    def analyze_python_files(self) -> Dict[str, List[str]]:
        """
        Scan Python files and extract docstrings/comments.
        Returns dict of {category: [documentation strings]}
        """
        docs = {
            'modules': [],
            'classes': [],
            'functions': [],
            'important_comments': []
        }
        
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if not file.endswith('.py'):
                    continue
                    
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    tree = ast.parse(content)
                    
                    if ast.get_docstring(tree):
                        docs['modules'].append(f"{file}: {ast.get_docstring(tree)}")
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef) and ast.get_docstring(node):
                            docs['classes'].append(f"{node.name}: {ast.get_docstring(node)}")
                        elif isinstance(node, ast.FunctionDef) and ast.get_docstring(node):
                            docs['functions'].append(f"{node.name}: {ast.get_docstring(node)}")
                            
                    lines = content.split('\n')
                    important_comments = [line.strip('# :') for line in lines 
                                       if line.strip().startswith('#:')]
                    if important_comments:
                        docs['important_comments'].extend(important_comments)
                        
                except Exception as e:
                    logging.warning(f"Failed to analyze {file}: {e}")
                    
        return docs
    
    def analyze_repository(self) -> Dict[str, List[str]]:
        """
        Analyze Python files in the repository using GitHub API
        """
        docs = {
            'modules': [],
            'classes': [],
            'functions': [],
            'important_comments': []
        }
        
        try:
            contents = self.repo.get_contents("")
            
            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":
                    contents.extend(self.repo.get_contents(file_content.path))
                elif file_content.path.endswith('.py'):
                    self._analyze_file(file_content, docs)
                    
        except Exception as e:
            logging.warning(f"Error analyzing repository: {e}")
            
        return docs
    
    def _analyze_file(self, file_content: ContentFile, docs: Dict[str, List[str]]) -> None:
        try:
            # Decode content from base64
            content = base64.b64decode(file_content.content).decode('utf-8')
            
            # Parse Python file
            tree = ast.parse(content)
            
            # Get module docstring
            if ast.get_docstring(tree):
                docs['modules'].append(f"{file_content.path}: {ast.get_docstring(tree)}")
            
            # Visit all nodes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and ast.get_docstring(node):
                    docs['classes'].append(f"{node.name}: {ast.get_docstring(node)}")
                elif isinstance(node, ast.FunctionDef) and ast.get_docstring(node):
                    docs['functions'].append(f"{node.name}: {ast.get_docstring(node)}")
                    
            # Extract important comments
            lines = content.split('\n')
            important_comments = [line.strip('# :') for line in lines 
                               if line.strip().startswith('#:')]
            if important_comments:
                docs['important_comments'].extend(important_comments)
                
        except Exception as e:
            logging.warning(f"Failed to analyze {file_content.path}: {e}")