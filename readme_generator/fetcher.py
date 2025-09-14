"""
GitHub data fetching module.

This module handles all GitHub API interactions for fetching repository data
and commit history using PyGithub.
"""

import datetime
import logging
from typing import List, Optional

from .models import CommitInfo, RepoMeta

# External libs
try:
    from github import Github, Repository, Commit
except Exception as e:
    raise RuntimeError("PyGithub is required. Install with: pip install PyGithub") from e

# Set up logging
logger = logging.getLogger("readme-generator.fetcher")


class GitHubFetcher:
    """
    Fetch commits and repository metadata from GitHub using PyGithub.

    This class handles all interactions with the GitHub API, including
    authentication, rate limiting, and error handling.

    Args:
        token: Personal access token (or None for unauthenticated, but rate-limited).
    """

    def __init__(self, token: Optional[str] = None) -> None:
        """
        Initialize the GitHub client.
        
        Args:
            token: GitHub personal access token for authentication.
                  If None, uses unauthenticated access (rate limited).
        """
        try:
            self._g = Github(login_or_token=token) if token else Github()
            logger.debug("GitHub client initialized (authenticated=%s)", bool(token))
        except Exception as e:
            logger.error("Failed to initialize GitHub client: %s", e)
            raise RuntimeError(f"GitHub client initialization failed: {e}") from e

    def fetch_repo_meta(self, owner: str, repo_name: str) -> RepoMeta:
        """
        Fetch repository metadata from GitHub.
        
        Args:
            owner: Repository owner username
            repo_name: Repository name
            
        Returns:
            RepoMeta object containing repository metadata
            
        Raises:
            RuntimeError: If repository cannot be accessed or found
        """
        try:
            repo: Repository.Repository = self._g.get_repo(f"{owner}/{repo_name}")
            
            # Safely fetch license information
            license_name = None
            try:
                lic = repo.get_license()
                license_name = lic.license.name
            except Exception as e:
                # Repository may not have license or permission to fetch
                logger.debug("Could not fetch license for %s/%s: %s", owner, repo_name, e)
                license_name = None

            meta = RepoMeta(
                full_name=repo.full_name,
                description=repo.description,
                url=repo.html_url,
                license_name=license_name,
                default_branch=repo.default_branch,
            )
            
            logger.info("Fetched metadata for %s", meta.full_name)
            return meta
            
        except Exception as e:
            error_msg = f"Failed to fetch repository metadata for {owner}/{repo_name}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def fetch_commits(self, owner: str, repo_name: str, max_commits: int = 500) -> List[CommitInfo]:
        """
        Fetch commit history from GitHub repository.
        
        Fetches commits in reverse chronological order (most recent first).
        
        Args:
            owner: Repository owner username
            repo_name: Repository name
            max_commits: Maximum number of commits to fetch (default: 500)
            
        Returns:
            List of CommitInfo objects representing the commit history
            
        Raises:
            RuntimeError: If commits cannot be fetched
        """
        try:
            repo: Repository.Repository = self._g.get_repo(f"{owner}/{repo_name}")
            commits = repo.get_commits()  # returns PaginatedList
            result: List[CommitInfo] = []
            count = 0
            
            logger.info("Fetching up to %d commits from %s/%s", max_commits, owner, repo_name)
            
            for c in commits:
                if count >= max_commits:
                    break
                    
                try:
                    commit_obj: Commit.Commit = c.commit
                    
                    # Extract author information with fallbacks
                    author_name = None
                    if c.author:
                        author_name = c.author.login
                    elif commit_obj.author and commit_obj.author.name:
                        author_name = commit_obj.author.name
                    
                    # Extract commit date with fallback
                    date = (commit_obj.author.date 
                           if commit_obj.author and commit_obj.author.date 
                           else datetime.datetime.now(datetime.timezone.utc))
                    
                    # Clean commit message
                    msg = commit_obj.message.strip()
                    
                    result.append(CommitInfo(
                        sha=c.sha, 
                        author=author_name, 
                        date=date, 
                        message=msg
                    ))
                    count += 1
                    
                except Exception as e:
                    logger.debug("Skipping commit due to error: %s", e)
                    continue
            
            logger.info("Successfully fetched %d commits from %s/%s", len(result), owner, repo_name)
            return result
            
        except Exception as e:
            error_msg = f"Failed to fetch commits for {owner}/{repo_name}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e