"""
summarizer.py
-------------
Module for summarizing GitHub commit history into clean,
Markdown-ready sections for README generation.

Usage:
    from summarizer import summarize_commit_history

    sections = summarize_commit_history(commit_messages, repo_info)
"""

import re
from collections import defaultdict
from typing import Dict, List, Tuple

try:
    import spacy
    NLP = spacy.load("en_core_web_sm")
except Exception:
    NLP = None  # fallback if spaCy not installed


def categorize_commits(commits: List[str]) -> Dict[str, List[str]]:
    """
    Categorize commits into groups using Conventional Commit prefixes
    or fallback keyword detection for non-standard repos.
    """
    categories = defaultdict(list)

    for msg in commits:
        lowered = msg.lower().strip()

        # Conventional Commit prefixes
        if lowered.startswith("feat"):
            categories["features"].append(msg)
        elif lowered.startswith("fix"):
            categories["fixes"].append(msg)
        elif lowered.startswith("docs"):
            categories["docs"].append(msg)
        elif lowered.startswith("refactor"):
            categories["refactor"].append(msg)
        elif lowered.startswith("test"):
            categories["tests"].append(msg)

        else:
            # Fallback keyword rules
            if re.search(r"\b(add|implement|introduce|support|feature)\b", lowered):
                categories["features"].append(msg)
            elif re.search(r"\b(fix|bug|issue|error|crash|resolve)\b", lowered):
                categories["fixes"].append(msg)
            elif re.search(r"\b(doc|readme|guide|tutorial)\b", lowered):
                categories["docs"].append(msg)
            elif re.search(r"\b(refactor|restructure|cleanup|format)\b", lowered):
                categories["refactor"].append(msg)
            elif re.search(r"\b(test|coverage|ci|pipeline)\b", lowered):
                categories["tests"].append(msg)
            else:
                categories["other"].append(msg)

    return categories



def _nlp_summarize(messages: List[str], max_phrases: int = 5) -> str:
    """
    Summarize commit messages into key phrases using spaCy.
    Falls back to simple join if spaCy unavailable.

    Args:
        messages: List of commit messages
        max_phrases: Maximum number of phrases to return

    Returns:
        str: Summarized text
    """
    if not messages:
        return ""

    if NLP:
        doc = NLP(" ".join(messages))
        phrases = [chunk.text.strip() for chunk in doc.noun_chunks if len(chunk.text.split()) > 1]
        unique_phrases = list(dict.fromkeys(phrases))  # dedupe, preserve order
        return ", ".join(unique_phrases[:max_phrases])
    else:
        # fallback: join first few messages
        return "; ".join(messages[:max_phrases])


def format_category_summary(messages: List[str]) -> List[str]:
    """
    Convert raw commit messages into clean bullet points.

    Args:
        messages: List of commit messages

    Returns:
        List[str]: bullet-point style summaries
    """
    summaries = []
    for msg in messages:
        # remove prefix like "feat:" or "fix:"
        clean = re.sub(r"^\w+:\s*", "", msg).strip()
        # keep it short
        summaries.append(f"- {clean}")
    return summaries


def summarize_commit_history(commits: List[str], repo_info: Dict) -> Dict[str, str]:
    """
    High-level summarization of commit history.

    Args:
        commits: List of commit messages
        repo_info: Dict with repo metadata (name, description, language, topics)

    Returns:
        Dict with sections: { "introduction": ..., "features": ..., "fixes": ... }
    """
    categories = categorize_commits(commits)

    # Introduction: use repo description if available
    intro = repo_info.get("description") or f"{repo_info['name']} is a {repo_info.get('language', 'project')} repository."
    intro += "\n\nThis project includes " + _nlp_summarize(commits)

    # Features
    features = "\n".join(format_category_summary(categories.get("features", [])))

    # Fixes
    fixes = "\n".join(format_category_summary(categories.get("fixes", [])))

    # Docs
    docs = "\n".join(format_category_summary(categories.get("docs", [])))

    return {
        "introduction": intro.strip(),
        "features": features.strip() or "No major features listed.",
        "fixes": fixes.strip() or "No major fixes listed.",
        "docs": docs.strip() or "No documentation changes listed."
    }
