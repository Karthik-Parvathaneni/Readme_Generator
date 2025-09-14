"""
Commit parsing and categorization module.

This module handles parsing commit messages using Conventional Commits format
and categorizing commits by type for further processing.
"""

import collections
import re
from typing import Dict, List, Optional, Tuple

from .models import CommitInfo


class CommitParser:
    """
    Parse commit messages into (type, scope, description, body) using Conventional Commits style.
    Fallback: tries to infer type via simple heuristics if not matching conventional pattern.
    """

    CONVENTIONAL_RE = re.compile(r"^(?P<type>feat|fix|docs|style|refactor|perf|test|chore)(\((?P<scope>[^)]+)\))?(!)?:\s*(?P<desc>.+)", re.I)

    @staticmethod
    def parse(message: str) -> Tuple[str, Optional[str], str, Optional[str]]:
        """
        Parse commit message.

        Returns:
            (type, scope, short_description, body)
        """
        lines = message.splitlines()
        first = lines[0] if lines else ""
        m = CommitParser.CONVENTIONAL_RE.match(first)
        if m:
            ctype = m.group("type").lower()
            scope = m.group("scope")
            desc = m.group("desc").strip()
            body = "\n".join(lines[1:]).strip() if len(lines) > 1 else None
            return ctype, scope, desc, body
        # heuristic fallback
        lowered = first.lower()
        guessed = "chore"
        for t in ("feat", "fix", "docs", "refactor", "perf", "test", "style"):
            if lowered.startswith(t) or f"{t}:" in lowered or t in lowered.split():
                guessed = t
                break
        desc = first.strip()
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else None
        return guessed, None, desc, body


class CommitCategorizer:
    """
    Categorize commits by type using the CommitParser.
    
    Groups commits into categories (feat, fix, docs, etc.) for further processing.
    """

    def __init__(self):
        """Initialize the categorizer."""
        pass

    def categorize(self, commits: List[CommitInfo]) -> Dict[str, List[CommitInfo]]:
        """
        Group commits by their type.

        Args:
            commits: List of CommitInfo objects to categorize

        Returns:
            Dictionary mapping commit type -> list of commits of that type
        """
        groups: Dict[str, List[CommitInfo]] = collections.defaultdict(list)
        
        for commit in commits:
            commit_type, scope, desc, body = CommitParser.parse(commit.message)
            groups[commit_type].append(commit)
        
        # Convert defaultdict to regular dict for cleaner interface
        return dict(groups)

    def get_commit_types(self, commits: List[CommitInfo]) -> List[str]:
        """
        Get all unique commit types found in the commit list.

        Args:
            commits: List of CommitInfo objects

        Returns:
            List of unique commit types found
        """
        types = set()
        for commit in commits:
            commit_type, _, _, _ = CommitParser.parse(commit.message)
            types.add(commit_type)
        
        return sorted(list(types))

    def get_commits_by_type(self, commits: List[CommitInfo], commit_type: str) -> List[CommitInfo]:
        """
        Get all commits of a specific type.

        Args:
            commits: List of CommitInfo objects
            commit_type: The type of commits to retrieve (e.g., 'feat', 'fix')

        Returns:
            List of commits matching the specified type
        """
        matching_commits = []
        
        for commit in commits:
            parsed_type, _, _, _ = CommitParser.parse(commit.message)
            if parsed_type == commit_type:
                matching_commits.append(commit)
        
        return matching_commits