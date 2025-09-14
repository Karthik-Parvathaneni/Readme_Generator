"""
README Generator - A modular tool for generating README files from GitHub commit history.
"""

from .models import CommitInfo, RepoMeta
from .fetcher import GitHubFetcher
from .generator import ReadmeGenerator
from .summarizer import CommitSummarizer
from .parser import CommitParser, CommitCategorizer
from .main import main

__all__ = [
    'CommitInfo', 
    'RepoMeta', 
    'GitHubFetcher', 
    'ReadmeGenerator', 
    'CommitSummarizer',
    'CommitParser',
    'CommitCategorizer',
    'main'
]