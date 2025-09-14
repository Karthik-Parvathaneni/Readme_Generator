#!/usr/bin/env python3
"""
readme_generator.py

Generate a project README from a GitHub repo's commit history.

Usage (example):
    python readme_generator.py --user octocat --repo Hello-World --token GITHUB_TOKEN --output README.md

Primary components:
 - GitHubFetcher: fetches commits and repo metadata (uses PyGithub).
 - CommitSummarizer: groups commits and produces short summaries using local NLP (NLTK).
 - ReadmeGenerator: creates a Markdown README from the summaries and repo metadata.

Design notes:
 - Commit messages are parsed with Conventional Commits in mind (feat, fix, docs, etc.).
 - The code is written to be easily extensible: add a CodeAnalyzer component later to read the repository files.
"""

from __future__ import annotations
import argparse
import collections
import datetime
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from summarizer import summarize_commit_history

# External libs
try:
    from github import Github, Repository, Commit
except Exception as e:
    raise RuntimeError("PyGithub is required. Install with: pip install PyGithub") from e

# For summarization
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
except Exception:
    # We'll raise a helpful error later; user can pip install nltk and run nltk.download('punkt','stopwords')
    nltk = None

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("readme-generator")

# ---------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------
@dataclass
class CommitInfo:
    sha: str
    author: Optional[str]
    date: datetime.datetime
    message: str


@dataclass
class RepoMeta:
    full_name: str
    description: Optional[str]
    url: str
    license_name: Optional[str]
    default_branch: str


# ---------------------------------------------------------------------
# GitHub fetcher
# ---------------------------------------------------------------------
class GitHubFetcher:
    """
    Fetch commits and repository metadata from GitHub using PyGithub.

    Args:
        token: Personal access token (or None for unauthenticated, but rate-limited).
    """

    def __init__(self, token: Optional[str] = None) -> None:
        self._g = Github(login_or_token=token) if token else Github()
        logger.debug("GitHub client initialized (authenticated=%s)", bool(token))

    def fetch_repo_meta(self, owner: str, repo_name: str) -> RepoMeta:
        """Return repository metadata."""
        repo: Repository.Repository = self._g.get_repo(f"{owner}/{repo_name}")
        license_name = None
        try:
            lic = repo.get_license()
            license_name = lic.license.name
        except Exception:
            # repo may not have license or permission to fetch
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

    def fetch_commits(self, owner: str, repo_name: str, max_commits: int = 500) -> List[CommitInfo]:
        """
        Fetch commit history (most recent first) and return as CommitInfo list.

        - max_commits limits how many commits to fetch (safe default).
        """
        repo: Repository.Repository = self._g.get_repo(f"{owner}/{repo_name}")
        commits = repo.get_commits()  # returns PaginatedList
        result: List[CommitInfo] = []
        count = 0
        for c in commits:
            if count >= max_commits:
                break
            try:
                commit_obj: Commit.Commit = c.commit
                author_name = None
                if c.author:
                    author_name = c.author.login
                elif commit_obj.author and commit_obj.author.name:
                    author_name = commit_obj.author.name

                date = commit_obj.author.date if commit_obj.author and commit_obj.author.date else datetime.datetime.utcnow()
                msg = commit_obj.message.strip()
                result.append(CommitInfo(sha=c.sha, author=author_name, date=date, message=msg))
                count += 1
            except Exception as e:
                logger.debug("Skipping commit due to error: %s", e)
                continue
        logger.info("Fetched %d commits", len(result))
        return result


# ---------------------------------------------------------------------
# Commit parsing and summarization
# ---------------------------------------------------------------------
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


class CommitSummarizer:
    """
    Summarize a list of commits into group summaries.

    Strategy:
     - Parse commits into types (feat, fix, docs, chore, etc.)
     - For each type, extract key short descriptions (top-N) using a small frequency-based scoring of words
       from commit descriptions and bodies.
    """

    def __init__(self, use_gemini: bool = False) -> None:
        self.use_gemini = use_gemini
        # Prepare NLTK resources if available
        if nltk:
            try:
                nltk.data.find("tokenizers/punkt")
            except LookupError:
                logger.info("NLTK punkt not found, attempting to download")
                nltk.download("punkt", quiet=True)
            try:
                nltk.data.find("corpora/stopwords")
            except LookupError:
                logger.info("NLTK stopwords not found, attempting to download")
                nltk.download("stopwords", quiet=True)

    def summarize(self, commits: List[CommitInfo], top_n_per_type: int = 5) -> Dict[str, List[str]]:
        """
        Return dictionary mapping commit type -> list of summary points.

        Example:
            {
                "feat": ["Add signup flow", "Add OAuth login"],
                "fix": ["Fix crash when X", ...],
                ...
            }
        """
        groups: Dict[str, List[CommitInfo]] = collections.defaultdict(list)
        for c in commits:
            ctype, scope, desc, body = CommitParser.parse(c.message)
            groups[ctype].append(c)

        summaries: Dict[str, List[str]] = {}

        for ctype, items in groups.items():
            # gather candidate sentences (desc + first sentence of body)
            candidates: List[str] = []
            for c in items:
                _, _, desc, body = CommitParser.parse(c.message)
                if desc:
                    candidates.append(desc)
                if body:
                    # take first sentence of body
                    sents = sent_tokenize(body) if nltk else [body.split("\n")[0]]
                    if sents:
                        candidates.append(sents[0])

            # If Gemini is allowed and the user explicitly opts in / token provided,
            # we could call Gemini API here to compress/abstract. For now we prefer local methods.
            if self.use_gemini:
                # Placeholder: call to Gemini for abstractive summarization if needed.
                # Example:
                # gemini_summary = call_gemini_api(candidates, max_tokens=200)
                # summaries[ctype] = gemini_summary
                pass

            # Use a simple frequency-based ranking for extractive summarization
            ranked = self._rank_candidates(candidates)
            summaries[ctype] = ranked[:top_n_per_type]

        return summaries

    def _rank_candidates(self, candidates: List[str]) -> List[str]:
        """
        Score each candidate sentence by the sum of word frequencies (ignoring stopwords).
        Return candidates sorted by score descending, de-duplicated while preserving order.
        """
        if not candidates:
            return []

        stop_words = set(stopwords.words("english")) if nltk else set()
        word_freq = collections.Counter()
        tokenized_candidates: List[List[str]] = []
        for cand in candidates:
            words = [w.lower() for w in word_tokenize(cand)] if nltk else cand.lower().split()
            words = [re.sub(r"\W+", "", w) for w in words if w and re.sub(r"\W+", "", w)]
            filtered = [w for w in words if w not in stop_words]
            tokenized_candidates.append(filtered)
            word_freq.update(filtered)

        # Score candidates
        cand_scores: List[Tuple[str, float]] = []
        for i, cand in enumerate(candidates):
            tokens = tokenized_candidates[i]
            score = sum(word_freq.get(t, 0) for t in tokens)
            cand_scores.append((cand, score))

        # Sort by score desc, preserve original tiebreak order for equal scores via stable sort
        cand_scores.sort(key=lambda x: x[1], reverse=True)

        # de-duplicate (case-insensitive)
        seen = set()
        ordered: List[str] = []
        for cand, _ in cand_scores:
            key = cand.lower()
            if key not in seen:
                seen.add(key)
                ordered.append(cand)
        return ordered


# ---------------------------------------------------------------------
# README generator
# ---------------------------------------------------------------------
class ReadmeGenerator:
    """
    Compose a README.md string from repo metadata and commit summaries.

    Methods:
     - generate_markdown(meta, summaries, commits) -> str
    """

    def __init__(self, include_commit_examples: bool = True) -> None:
        self.include_commit_examples = include_commit_examples

    def generate_markdown(self, meta: RepoMeta, summaries: Dict[str, List[str]], commits: List[CommitInfo]) -> str:
        """
        Build a markdown-formatted README string.
        """
        lines: List[str] = []
        # Title & description
        lines.append(f"# {meta.full_name}\n")
        if meta.description:
            lines.append(f"{meta.description}\n")
        lines.append(f"**Repository:** [{meta.url}]({meta.url})\n")
        if meta.license_name:
            lines.append(f"**License:** {meta.license_name}\n")

        # Generated note
        lines.append("---\n")
        lines.append(f"_This README was generated automatically from the repository's commit history on {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_\n")

        # Introduction (short)
        lines.append("## Introduction\n")
        intro = self._build_intro(meta, summaries)
        lines.append(intro + "\n")

        # Features (from feat commits)
        lines.append("## Features\n")
        features = summaries.get("feat", [])
        if features:
            for f in features:
                lines.append(f"- {f}")
        else:
            lines.append("- Feature list is not found from commit messages. Please add features manually or run extended analysis.")
        lines.append("")  # blank line

        # Bug fixes / Improvements
        fixes = summaries.get("fix", []) + summaries.get("perf", []) + summaries.get("refactor", [])
        if fixes:
            lines.append("## Fixes & Improvements\n")
            for f in fixes:
                lines.append(f"- {f}")
            lines.append("")

        # Documentation
        docs = summaries.get("docs", [])
        lines.append("## Documentation\n")
        if docs:
            for d in docs:
                lines.append(f"- {d}")
        else:
            lines.append("- Documentation updated in commit history; check docs/ or README sources in the repository.")
        lines.append("")

        # Installation (try to infer)
        lines.append("## Installation\n")
        lines.append("```bash")
        lines.append("# Example: replace with repository specific instructions")
        lines.append("pip install -r requirements.txt")
        lines.append("```")
        lines.append("")

        # Usage
        lines.append("## Usage\n")
        lines.append("Describe how to use the project. Inferred usage points from commits:")
        usage_points = summaries.get("feat", [])[:5]  # reuse features as usage hints
        if usage_points:
            for u in usage_points:
                lines.append(f"- {u}")
        else:
            lines.append("- Usage details are not clear from commit messages; please add usage examples.")
        lines.append("")

        # Contribution
        lines.append("## Contribution\n")
        lines.append("Contributions are welcome. Prefer using Conventional Commits in commit messages.\n")
        if self.include_commit_examples:
            lines.append("### Example commit types")
            lines.append("- `feat(scope): add meaningful feature`")
            lines.append("- `fix(scope): fix bug`")
            lines.append("- `docs: update documentation`")
            lines.append("")

        # Recent activity / changelog (derived from commits)
        lines.append("## Recent activity (derived from commits)\n")
        for c in commits[:10]:
            short_msg = c.message.splitlines()[0]
            date = c.date.strftime("%Y-%m-%d")
            author = c.author or "unknown"
            lines.append(f"- `{c.sha[:7]}` {date} — {short_msg} ({author})")
        lines.append("")

        # License and footer
        if meta.license_name:
            lines.append("## License\n")
            lines.append(f"This project is licensed under the {meta.license_name}.\n")

        lines.append("---\n")
        lines.append("_Generated by readme_generator.py_")

        return "\n".join(lines)

    def _build_intro(self, meta: RepoMeta, summaries: Dict[str, List[str]]) -> str:
        """
        Construct a short introduction using repo description and feature summary.
        """
        parts = []
        if meta.description:
            parts.append(meta.description.strip())
        feats = summaries.get("feat", [])
        if feats:
            parts.append("Key features include: " + ", ".join(f"{f}" for f in feats[:3]) + ".")
        return " ".join(parts) if parts else "No description available. Please update the repository description."


# ---------------------------------------------------------------------
# CLI glue
# ---------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Generate README from GitHub commit history.")
    parser.add_argument("--user", "-u", required=True, help="GitHub owner/username")
    parser.add_argument("--repo", "-r", required=True, help="Repository name")
    parser.add_argument("--token", "-t", required=False, help="GitHub token (recommended to avoid rate limits)")
    parser.add_argument("--output", "-o", default="README_GENERATED.md", help="Output README filename")
    parser.add_argument("--max-commits", type=int, default=500, help="Maximum number of commits to fetch")
    parser.add_argument("--use-gemini", action="store_true", help="Use Gemini API for abstractive summarization (placeholder)")
    args = parser.parse_args()

    # Check NLTK availability
    if nltk is None:
        logger.error("NLTK is required. Install with `pip install nltk` and run `python -m nltk.downloader punkt stopwords`.")
        raise SystemExit(1)

    # Fetch data
    fetcher = GitHubFetcher(token=args.token)
    meta = fetcher.fetch_repo_meta(args.user, args.repo)
    commits = fetcher.fetch_commits(args.user, args.repo, max_commits=args.max_commits)

    # Summarize
    summarizer = CommitSummarizer(use_gemini=args.use_gemini)
    summaries = summarizer.summarize(commits)

    # Generate readme
    generator = ReadmeGenerator(include_commit_examples=True)
    md = generator.generate_markdown(meta, summaries, commits)

    # Write file
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)
    logger.info("Wrote README to %s", args.output)
    print(f"Wrote README to {args.output}")


if __name__ == "__main__":
    main()
