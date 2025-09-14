#!/usr/bin/env python3
"""
Main driver script for the README generator.

This script provides the command-line interface and coordinates all modules
to generate comprehensive README files from GitHub commit history.

Usage (example):
    python -m readme_generator.main --user octocat --repo Hello-World --token GITHUB_TOKEN --output README.md
"""

import argparse
import logging
import sys
from typing import Optional

from .fetcher import GitHubFetcher
from .generator import ReadmeGenerator
from .summarizer import CommitSummarizer

# For summarization
try:
    import nltk
except Exception:
    # We'll raise a helpful error later; user can pip install nltk and run nltk.download('punkt','stopwords')
    nltk = None

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("readme-generator")


def main() -> None:
    """
    Main entry point for the README generator.
    
    Parses command line arguments, coordinates all modules, and generates
    the README file while maintaining backward compatibility with the
    original monolithic version.
    """
    parser = argparse.ArgumentParser(description="Generate README from GitHub commit history.")
    parser.add_argument("--user", "-u", required=True, help="GitHub owner/username")
    parser.add_argument("--repo", "-r", required=True, help="Repository name")
    parser.add_argument("--token", "-t", required=False, help="GitHub token (recommended to avoid rate limits)")
    parser.add_argument("--output", "-o", default="README_GENERATED.md", help="Output README filename")
    parser.add_argument("--max-commits", type=int, default=500, help="Maximum number of commits to fetch")
    parser.add_argument("--use-gemini", action="store_true", help="Use Gemini API for abstractive summarization (placeholder)")
    args = parser.parse_args()

    try:
        # Check NLTK availability
        if nltk is None:
            logger.error("NLTK is required. Install with `pip install nltk` and run `python -m nltk.downloader punkt stopwords`.")
            raise SystemExit(1)

        logger.info("Starting README generation for %s/%s", args.user, args.repo)

        # Initialize GitHub fetcher
        logger.info("Initializing GitHub fetcher...")
        fetcher = GitHubFetcher(token=args.token)

        # Fetch repository metadata
        logger.info("Fetching repository metadata...")
        meta = fetcher.fetch_repo_meta(args.user, args.repo)

        # Fetch commit history
        logger.info("Fetching commit history (max: %d commits)...", args.max_commits)
        commits = fetcher.fetch_commits(args.user, args.repo, max_commits=args.max_commits)

        if not commits:
            logger.warning("No commits found for repository %s/%s", args.user, args.repo)
            print(f"Warning: No commits found for repository {args.user}/{args.repo}")
            return

        # Generate commit summaries
        logger.info("Analyzing and summarizing %d commits...", len(commits))
        summarizer = CommitSummarizer(use_gemini=args.use_gemini)
        summaries = summarizer.summarize(commits)

        if not summaries:
            logger.warning("No commit summaries generated")
            print("Warning: No commit summaries could be generated")

        # Generate README markdown
        logger.info("Generating README markdown...")
        generator = ReadmeGenerator(include_commit_examples=True)
        md = generator.generate_markdown(meta, summaries, commits)

        # Write output file
        logger.info("Writing README to %s", args.output)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(md)

        logger.info("README generation completed successfully")
        print(f"✓ README generated successfully: {args.output}")
        print(f"  Repository: {meta.full_name}")
        print(f"  Commits analyzed: {len(commits)}")
        print(f"  Summary categories: {', '.join(summaries.keys()) if summaries else 'none'}")

    except KeyboardInterrupt:
        logger.info("README generation interrupted by user")
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error("README generation failed: %s", e)
        print(f"Error: README generation failed - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()