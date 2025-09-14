"""
Data models for the README generator.

This module contains the shared data structures used across all modules.
"""

import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class CommitInfo:
    """Represents a single commit with its metadata."""
    sha: str
    author: Optional[str]
    date: datetime.datetime
    message: str


@dataclass
class RepoMeta:
    """Repository metadata from GitHub."""
    full_name: str
    description: Optional[str]
    url: str
    license_name: Optional[str]
    default_branch: str