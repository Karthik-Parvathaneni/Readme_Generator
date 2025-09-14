"""
README Generation Module

This module contains the ReadmeGenerator class responsible for creating
comprehensive README markdown files from repository metadata and commit summaries.
"""

import datetime
from typing import Dict, List

from .models import CommitInfo, RepoMeta


class ReadmeGenerator:
    """
    Compose a README.md string from repo metadata and commit summaries.

    This class generates comprehensive README files with sections for features,
    fixes, documentation, project analysis, and recent activity based on
    commit history analysis.
    """

    def __init__(self, include_commit_examples: bool = True) -> None:
        """
        Initialize the README generator.
        
        Args:
            include_commit_examples: Whether to include commit format examples
                                   in the contribution section
        """
        self.include_commit_examples = include_commit_examples

    def generate_markdown(self, meta: RepoMeta, summaries: Dict[str, str], commits: List[CommitInfo]) -> str:
        """
        Build a markdown-formatted README string.
        
        Args:
            meta: Repository metadata including name, description, URL, license
            summaries: Dictionary mapping commit types to their summaries
            commits: List of commit information for recent activity
            
        Returns:
            Complete README markdown content as a string
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
        lines.append(f"_This README was generated automatically from the repository's commit history on {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n")

        # Introduction (short)
        lines.append("## Introduction\n")
        intro = self._build_introduction(meta, summaries)
        lines.append(intro + "\n")

        # Features (from feat commits)
        lines.append("## Features\n")
        features = summaries.get("feat", "")
        if features:
            lines.append(features + "\n")
        else:
            lines.append("No major features found in recent commit history. Please add feature descriptions manually.\n")

        # Bug fixes / Improvements
        fixes_content = []
        if summaries.get("fix"):
            fixes_content.append(summaries["fix"])
        if summaries.get("perf"):
            fixes_content.append(summaries["perf"])
        if summaries.get("refactor"):
            fixes_content.append(summaries["refactor"])
            
        if fixes_content:
            lines.append("## Fixes & Improvements\n")
            lines.append(" ".join(fixes_content) + "\n")

        # Documentation
        docs = summaries.get("docs", "")
        if docs:
            lines.append("## Documentation\n")
            lines.append(docs + "\n")

        # Installation (try to infer)
        lines.append("## Installation\n")
        lines.append("```bash")
        lines.append("# Example: replace with repository specific instructions")
        lines.append("pip install -r requirements.txt")
        lines.append("```")
        lines.append("")

        # Project Insights (new section)
        lines.append("## Project Analysis\n")
        lines.append(self._build_project_analysis(summaries, commits) + "\n")

        # Usage
        lines.append("## Usage\n")
        if summaries.get("feat"):
            lines.append("Based on recent development activity:\n")
            lines.append(summaries["feat"] + "\n")
            lines.append("Please refer to the documentation for detailed usage instructions.\n")
        else:
            lines.append("Usage details are not clear from commit messages. Please add usage examples manually.\n")

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
        recent_activity = self._format_recent_activity(commits)
        lines.append(recent_activity + "\n")

        # License and footer
        if meta.license_name:
            lines.append("## License\n")
            lines.append(f"This project is licensed under the {meta.license_name}.\n")

        lines.append("---\n")
        lines.append("_Generated by readme_generator.py_")

        return "\n".join(lines)

    def _build_introduction(self, meta: RepoMeta, summaries: Dict[str, str]) -> str:
        """
        Construct a comprehensive introduction using repo description and development activity.
        
        Args:
            meta: Repository metadata
            summaries: Commit type summaries
            
        Returns:
            Formatted introduction text
        """
        parts = []
        if meta.description:
            parts.append(meta.description.strip())
        
        # Analyze development activity patterns
        activity_summary = []
        
        if summaries.get("feat"):
            activity_summary.append("active feature development")
        if summaries.get("fix"):
            activity_summary.append("comprehensive bug fixing")
        if summaries.get("refactor"):
            activity_summary.append("code quality improvements")
        if summaries.get("docs"):
            activity_summary.append("documentation enhancements")
        if summaries.get("test"):
            activity_summary.append("testing infrastructure development")
        if summaries.get("perf"):
            activity_summary.append("performance optimizations")
        
        if activity_summary:
            if len(activity_summary) == 1:
                parts.append(f"This project shows {activity_summary[0]} with a focus on delivering robust and reliable software.")
            elif len(activity_summary) == 2:
                parts.append(f"Recent development demonstrates {activity_summary[0]} and {activity_summary[1]}, indicating a well-maintained and actively evolving codebase.")
            else:
                activity_text = ", ".join(activity_summary[:-1]) + f", and {activity_summary[-1]}"
                parts.append(f"The project exhibits strong development momentum with {activity_text}, showcasing a comprehensive approach to software development and maintenance.")
        
        # Add development maturity indicator
        total_commits = sum(1 for s in summaries.values() if s)
        if total_commits >= 4:
            parts.append("The extensive commit history demonstrates a mature, well-maintained project with consistent development practices.")
        elif total_commits >= 2:
            parts.append("The project shows active development with regular updates and improvements.")
            
        return " ".join(parts) if parts else "No description available. Please update the repository description."

    def _build_project_analysis(self, summaries: Dict[str, str], commits: List[CommitInfo]) -> str:
        """
        Build insights about the project based on commit analysis.
        
        Args:
            summaries: Commit type summaries
            commits: List of commit information
            
        Returns:
            Formatted project analysis text
        """
        insights = []
        
        # Development activity analysis
        total_commits = len(commits)
        insights.append(f"**Development Activity**: Analysis of {total_commits} recent commits reveals:")
        
        # Categorize development focus
        categories = []
        if summaries.get("feat"):
            categories.append("feature development")
        if summaries.get("fix"):
            categories.append("stability improvements")
        if summaries.get("refactor"):
            categories.append("code quality enhancements")
        if summaries.get("docs"):
            categories.append("documentation improvements")
        if summaries.get("test"):
            categories.append("testing infrastructure")
        if summaries.get("perf"):
            categories.append("performance optimizations")
        
        if categories:
            insights.append(f"- Primary focus areas: {', '.join(categories)}")
        
        # Commit frequency analysis
        if commits:
            # Analyze commit dates to determine development pace
            recent_commits = [c for c in commits[:30]]  # Last 30 commits
            if len(recent_commits) >= 10:
                insights.append("- **Development Pace**: High activity with frequent commits indicating active maintenance")
            elif len(recent_commits) >= 5:
                insights.append("- **Development Pace**: Moderate activity with regular updates")
            else:
                insights.append("- **Development Pace**: Steady development with periodic updates")
        
        # Author diversity (if available)
        authors = set(c.author for c in commits if c.author)
        if len(authors) > 10:
            insights.append(f"- **Community**: Active community with {len(authors)}+ contributors")
        elif len(authors) > 3:
            insights.append(f"- **Team**: Collaborative development with {len(authors)} active contributors")
        elif len(authors) > 1:
            insights.append(f"- **Collaboration**: Small team development with {len(authors)} contributors")
        
        # Quality indicators
        quality_indicators = []
        if summaries.get("test"):
            quality_indicators.append("comprehensive testing")
        if summaries.get("docs"):
            quality_indicators.append("thorough documentation")
        if summaries.get("refactor"):
            quality_indicators.append("code quality focus")
        
        if quality_indicators:
            insights.append(f"- **Quality Assurance**: Emphasis on {', '.join(quality_indicators)}")
        
        return "\n".join(insights)

    def _format_recent_activity(self, commits: List[CommitInfo]) -> str:
        """
        Format recent commit activity for display in README.
        
        Args:
            commits: List of commit information
            
        Returns:
            Formatted recent activity section
        """
        lines = []
        for c in commits[:10]:
            short_msg = c.message.splitlines()[0]
            date = c.date.strftime("%Y-%m-%d")
            author = c.author or "unknown"
            lines.append(f"- `{c.sha[:7]}` {date} — {short_msg} ({author})")
        
        return "\n".join(lines)