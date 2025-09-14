"""
Commit summarization module for the README generator.

This module provides detailed commit summarization functionality using NLP techniques
to create comprehensive, intelligent summaries from categorized commits.
"""

import collections
import logging
import re
from typing import Dict, List

from .models import CommitInfo
from .parser import CommitParser

# For summarization
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
except Exception:
    # We'll raise a helpful error later; user can pip install nltk and run nltk.download('punkt','stopwords')
    nltk = None

# logging
logger = logging.getLogger("readme-generator")


class CommitSummarizer:
    """
    Summarize a list of commits into group summaries.

    Strategy:
     - Parse commits into types (feat, fix, docs, chore, etc.)
     - For each type, create plain text summaries describing what was accomplished
     - Use NLP techniques to extract key themes and create coherent descriptions
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

    def summarize(self, commits: List[CommitInfo]) -> Dict[str, str]:
        """
        Return dictionary mapping commit type -> plain text summary.

        Example:
            {
                "feat": "Added new authentication system with OAuth support and user signup flow...",
                "fix": "Resolved critical bugs including memory leaks and crash issues...",
                ...
            }
        """
        groups: Dict[str, List[CommitInfo]] = collections.defaultdict(list)
        for c in commits:
            ctype, scope, desc, body = CommitParser.parse(c.message)
            groups[ctype].append(c)

        summaries: Dict[str, str] = {}

        for ctype, items in groups.items():
            if not items:
                continue
                
            # Extract all descriptions and key terms
            descriptions = []
            all_text = []
            
            for c in items:
                _, scope, desc, body = CommitParser.parse(c.message)
                if desc:
                    descriptions.append(desc.strip())
                    all_text.append(desc.strip())
                if body:
                    # Take first meaningful sentence from body
                    sents = sent_tokenize(body) if nltk else [body.split("\n")[0]]
                    if sents and len(sents[0].strip()) > 10:
                        all_text.append(sents[0].strip())

            # Create plain text summary for this category
            summary = self._create_detailed_summary(ctype, descriptions, all_text)
            if summary:
                summaries[ctype] = summary

        return summaries

    def _create_detailed_summary(self, commit_type: str, descriptions: List[str], all_text: List[str]) -> str:
        """
        Create a detailed summary for a specific commit type.
        """
        if not descriptions:
            return ""

        # Get key themes and terms
        key_terms = self._extract_key_terms(all_text)
        
        # Create type-specific summary
        if commit_type == "feat":
            return self._summarize_features(descriptions, key_terms)
        elif commit_type == "fix":
            return self._summarize_fixes(descriptions, key_terms)
        elif commit_type == "docs":
            return self._summarize_docs(descriptions, key_terms)
        elif commit_type == "refactor":
            return self._summarize_refactor(descriptions, key_terms)
        elif commit_type == "test":
            return self._summarize_tests(descriptions, key_terms)
        elif commit_type == "perf":
            return self._summarize_performance(descriptions, key_terms)
        else:
            return self._summarize_general(commit_type, descriptions, key_terms)

    def _extract_key_terms(self, texts: List[str]) -> List[str]:
        """Extract key terms from commit messages using frequency analysis."""
        if not texts:
            return []
            
        stop_words = set(stopwords.words("english")) if nltk else {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'
        }
        
        # Combine all text and extract meaningful terms
        all_text = " ".join(texts).lower()
        words = word_tokenize(all_text) if nltk else all_text.split()
        
        # Clean and filter words
        clean_words = []
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if len(clean_word) > 2 and clean_word not in stop_words and not clean_word.isdigit():
                clean_words.append(clean_word)
        
        # Get most frequent terms
        word_freq = collections.Counter(clean_words)
        return [word for word, count in word_freq.most_common(10) if count > 1]

    def _extract_themes(self, descriptions: List[str]) -> Dict[str, List[str]]:
        """Extract themes from commit descriptions for detailed analysis."""
        themes = collections.defaultdict(list)
        
        for desc in descriptions:
            desc_lower = desc.lower()
            
            # Authentication & Security themes
            if any(term in desc_lower for term in ['auth', 'login', 'signup', 'user', 'security', 'token', 'oauth', 'permission']):
                themes['authentication'].append(desc)
            
            # API & Backend themes
            if any(term in desc_lower for term in ['api', 'endpoint', 'request', 'response', 'server', 'backend', 'service', 'route']):
                themes['api'].append(desc)
            
            # UI/UX themes
            if any(term in desc_lower for term in ['ui', 'interface', 'component', 'view', 'frontend', 'react', 'vue', 'angular', 'css', 'html']):
                themes['ui'].append(desc)
            
            # Performance themes
            if any(term in desc_lower for term in ['cache', 'performance', 'optimization', 'speed', 'memory', 'efficient', 'fast']):
                themes['performance'].append(desc)
            
            # Data themes
            if any(term in desc_lower for term in ['database', 'db', 'sql', 'query', 'data', 'model', 'schema', 'migration']):
                themes['data'].append(desc)
        
        return dict(themes)

    def _analyze_impact(self, commit_type: str, count: int, themes: Dict[str, List[str]]) -> str:
        """Analyze the impact of commits based on type and themes."""
        if count == 0:
            return ""
        
        impact_phrases = []
        
        if commit_type == "feat":
            if count >= 10:
                impact_phrases.append("significant feature expansion")
            elif count >= 5:
                impact_phrases.append("notable feature development")
            else:
                impact_phrases.append("targeted feature additions")
        
        elif commit_type == "fix":
            if count >= 15:
                impact_phrases.append("comprehensive bug resolution")
            elif count >= 8:
                impact_phrases.append("substantial stability improvements")
            else:
                impact_phrases.append("focused issue resolution")
        
        elif commit_type == "refactor":
            if count >= 8:
                impact_phrases.append("extensive code restructuring")
            elif count >= 4:
                impact_phrases.append("significant architectural improvements")
            else:
                impact_phrases.append("targeted code optimization")
        
        # Add theme-based impact analysis
        if len(themes) >= 3:
            impact_phrases.append("multi-area improvements")
        elif len(themes) == 2:
            impact_phrases.append("cross-functional enhancements")
        
        return ", ".join(impact_phrases) if impact_phrases else "general improvements"

    def _summarize_features(self, descriptions: List[str], key_terms: List[str]) -> str:
        """Create detailed summary for feature commits."""
        count = len(descriptions)
        if count == 0:
            return ""
        
        desc_text = " ".join(descriptions).lower()
        
        # Identify detailed themes and capabilities
        themes = {}
        
        # Authentication & Security
        if any(term in desc_text for term in ['auth', 'login', 'signup', 'user', 'security', 'token', 'oauth', 'permission']):
            auth_features = [d for d in descriptions if any(term in d.lower() for term in ['auth', 'login', 'signup', 'user', 'security', 'token'])]
            themes["Authentication & Security"] = f"Enhanced authentication system with {len(auth_features)} improvements including user management, security protocols, and access control mechanisms."
        
        # API & Backend
        if any(term in desc_text for term in ['api', 'endpoint', 'request', 'response', 'server', 'backend', 'service', 'route']):
            api_features = [d for d in descriptions if any(term in d.lower() for term in ['api', 'endpoint', 'request', 'response', 'server'])]
            themes["API & Backend Services"] = f"Expanded API capabilities with {len(api_features)} new endpoints and backend services, improving data handling and service integration."
        
        # UI/UX & Frontend
        if any(term in desc_text for term in ['ui', 'interface', 'component', 'view', 'frontend', 'react', 'vue', 'angular', 'css', 'html']):
            ui_features = [d for d in descriptions if any(term in d.lower() for term in ['ui', 'interface', 'component', 'view', 'frontend'])]
            themes["User Interface & Experience"] = f"Introduced {len(ui_features)} new UI components and interface improvements, enhancing user experience and visual design."
        
        # Performance & Optimization
        if any(term in desc_text for term in ['cache', 'performance', 'optimization', 'speed', 'memory', 'efficient', 'fast']):
            perf_features = [d for d in descriptions if any(term in d.lower() for term in ['cache', 'performance', 'optimization', 'speed'])]
            themes["Performance & Optimization"] = f"Implemented {len(perf_features)} performance enhancements including caching mechanisms, memory optimization, and speed improvements."
        
        # Data & Database
        if any(term in desc_text for term in ['database', 'db', 'sql', 'query', 'data', 'model', 'schema', 'migration']):
            data_features = [d for d in descriptions if any(term in d.lower() for term in ['database', 'db', 'sql', 'query', 'data', 'model'])]
            themes["Data Management"] = f"Enhanced data handling with {len(data_features)} database improvements, query optimizations, and data model enhancements."
        
        # Integration & Compatibility
        if any(term in desc_text for term in ['support', 'compatibility', 'integration', 'plugin', 'extension', 'platform']):
            integration_features = [d for d in descriptions if any(term in d.lower() for term in ['support', 'compatibility', 'integration', 'plugin'])]
            themes["Platform Integration"] = f"Added {len(integration_features)} new integrations and platform compatibility features, expanding ecosystem support."
        
        # Testing & Quality
        if any(term in desc_text for term in ['test', 'testing', 'coverage', 'quality', 'validation', 'check']):
            test_features = [d for d in descriptions if any(term in d.lower() for term in ['test', 'testing', 'coverage', 'quality'])]
            themes["Testing & Quality Assurance"] = f"Strengthened testing framework with {len(test_features)} new testing capabilities and quality assurance measures."
        
        # Build summary
        feature_text = "feature" if count == 1 else "features"
        summary_parts = [f"The project has seen significant feature development with {count} new {feature_text} implemented across multiple areas:"]
        
        for theme_name, theme_desc in themes.items():
            summary_parts.append(f"\n• **{theme_name}**: {theme_desc}")
        
        if not themes:
            # Fallback for unrecognized patterns
            key_areas = key_terms[:5] if key_terms else ["core functionality", "system capabilities"]
            summary_parts.append(f"\n• **Core Enhancements**: Implemented improvements across {', '.join(key_areas)} with focus on expanding system capabilities and user functionality.")
        
        return "".join(summary_parts)

    def _summarize_fixes(self, descriptions: List[str], key_terms: List[str]) -> str:
        """Create detailed summary for bug fix commits."""
        count = len(descriptions)
        if count == 0:
            return ""
            
        desc_text = " ".join(descriptions).lower()
        
        # Categorize fixes by type and severity
        fix_categories = {}
        
        # Critical & Stability Issues
        critical_fixes = [d for d in descriptions if any(term in d.lower() for term in ['crash', 'error', 'exception', 'fail', 'critical', 'fatal', 'hang'])]
        if critical_fixes:
            fix_categories["Critical Stability"] = f"Resolved {len(critical_fixes)} critical issues including application crashes, fatal errors, and system stability problems that could impact user experience."
        
        # Memory & Performance Issues
        memory_fixes = [d for d in descriptions if any(term in d.lower() for term in ['memory', 'leak', 'performance', 'slow', 'timeout', 'optimization'])]
        if memory_fixes:
            fix_categories["Memory & Performance"] = f"Fixed {len(memory_fixes)} performance-related issues including memory leaks, slow operations, and resource optimization problems."
        
        # UI/UX & Display Issues
        ui_fixes = [d for d in descriptions if any(term in d.lower() for term in ['ui', 'display', 'render', 'visual', 'layout', 'css', 'style', 'appearance'])]
        if ui_fixes:
            fix_categories["User Interface"] = f"Corrected {len(ui_fixes)} user interface issues including display problems, rendering bugs, and visual inconsistencies."
        
        # Security & Vulnerability Fixes
        security_fixes = [d for d in descriptions if any(term in d.lower() for term in ['security', 'vulnerability', 'exploit', 'xss', 'csrf', 'injection', 'auth'])]
        if security_fixes:
            fix_categories["Security"] = f"Addressed {len(security_fixes)} security vulnerabilities and authentication issues, strengthening system protection."
        
        # Data & Logic Issues
        data_fixes = [d for d in descriptions if any(term in d.lower() for term in ['data', 'database', 'query', 'logic', 'calculation', 'validation', 'parsing'])]
        if data_fixes:
            fix_categories["Data & Logic"] = f"Resolved {len(data_fixes)} data handling and business logic issues, improving accuracy and reliability."
        
        # API & Integration Issues
        api_fixes = [d for d in descriptions if any(term in d.lower() for term in ['api', 'endpoint', 'integration', 'connection', 'network', 'request', 'response'])]
        if api_fixes:
            fix_categories["API & Integration"] = f"Fixed {len(api_fixes)} API and integration problems, ensuring reliable external service communication."
        
        # Compatibility & Platform Issues
        compat_fixes = [d for d in descriptions if any(term in d.lower() for term in ['compatibility', 'platform', 'browser', 'version', 'support', 'deprecated'])]
        if compat_fixes:
            fix_categories["Compatibility"] = f"Improved {len(compat_fixes)} compatibility issues across different platforms, browsers, and system versions."
        
        # Build comprehensive summary
        issue_text = "issue" if count == 1 else "issues"
        summary_parts = [f"Comprehensive bug fixing effort with {count} {issue_text} resolved across multiple categories:"]
        
        for category_name, category_desc in fix_categories.items():
            summary_parts.append(f"\n• **{category_name}**: {category_desc}")
        
        if not fix_categories:
            # Fallback for unrecognized patterns
            summary_parts.append(f"\n• **General Improvements**: Fixed various issues improving overall system reliability, user experience, and code quality.")
        
        summary_parts.append(f"\n\nThese fixes collectively enhance system stability, improve user experience, and ensure robust operation across different use cases and environments.")
        
        return "".join(summary_parts)

    def _summarize_docs(self, descriptions: List[str], key_terms: List[str]) -> str:
        """Create detailed summary for documentation commits."""
        count = len(descriptions)
        if count == 0:
            return ""
            
        desc_text = " ".join(descriptions).lower()
        
        # Categorize documentation improvements
        doc_categories = {}
        
        # User Documentation
        user_docs = [d for d in descriptions if any(term in d.lower() for term in ['readme', 'guide', 'tutorial', 'getting started', 'quickstart', 'example'])]
        if user_docs:
            doc_categories["User Documentation"] = f"Enhanced user-facing documentation with {len(user_docs)} updates including guides, tutorials, examples, and getting started materials."
        
        # API Documentation
        api_docs = [d for d in descriptions if any(term in d.lower() for term in ['api', 'reference', 'docstring', 'endpoint', 'parameter', 'method'])]
        if api_docs:
            doc_categories["API Reference"] = f"Improved API documentation with {len(api_docs)} updates covering endpoints, parameters, methods, and technical references."
        
        # Code Documentation
        code_docs = [d for d in descriptions if any(term in d.lower() for term in ['comment', 'docstring', 'inline', 'code', 'function', 'class'])]
        if code_docs:
            doc_categories["Code Documentation"] = f"Strengthened code documentation with {len(code_docs)} improvements to inline comments, docstrings, and code explanations."
        
        # Installation & Setup
        setup_docs = [d for d in descriptions if any(term in d.lower() for term in ['install', 'setup', 'configuration', 'deployment', 'build'])]
        if setup_docs:
            doc_categories["Installation & Setup"] = f"Updated installation and setup documentation with {len(setup_docs)} improvements covering configuration, deployment, and build processes."
        
        # Troubleshooting & FAQ
        help_docs = [d for d in descriptions if any(term in d.lower() for term in ['troubleshoot', 'faq', 'problem', 'issue', 'help', 'support'])]
        if help_docs:
            doc_categories["Support Documentation"] = f"Enhanced support materials with {len(help_docs)} additions to troubleshooting guides, FAQs, and help resources."
        
        # Build comprehensive summary
        update_text = "update" if count == 1 else "updates"
        summary_parts = [f"Comprehensive documentation improvements with {count} {update_text} enhancing project accessibility and developer experience:"]
        
        for category_name, category_desc in doc_categories.items():
            summary_parts.append(f"\n• **{category_name}**: {category_desc}")
        
        if not doc_categories:
            # Fallback for unrecognized patterns
            summary_parts.append(f"\n• **General Documentation**: Improved project documentation covering various aspects of the codebase, usage instructions, and technical details.")
        
        summary_parts.append(f"\n\nThese documentation enhancements make the project more accessible to new users, provide better guidance for developers, and improve overall project maintainability.")
        
        return "".join(summary_parts)

    def _summarize_refactor(self, descriptions: List[str], key_terms: List[str]) -> str:
        """Create detailed summary for refactoring commits."""
        count = len(descriptions)
        if count == 0:
            return ""
            
        desc_text = " ".join(descriptions).lower()
        
        # Categorize refactoring efforts
        refactor_categories = {}
        
        # Code Structure & Architecture
        structure_refactors = [d for d in descriptions if any(term in d.lower() for term in ['structure', 'architecture', 'organize', 'modular', 'component', 'class'])]
        if structure_refactors:
            refactor_categories["Code Architecture"] = f"Restructured codebase architecture with {len(structure_refactors)} improvements focusing on modularity, component organization, and structural clarity."
        
        # Performance Optimization
        perf_refactors = [d for d in descriptions if any(term in d.lower() for term in ['performance', 'optimize', 'efficient', 'speed', 'memory', 'cache'])]
        if perf_refactors:
            refactor_categories["Performance Optimization"] = f"Optimized code performance through {len(perf_refactors)} refactoring efforts targeting efficiency, speed improvements, and resource utilization."
        
        # Code Quality & Maintainability
        quality_refactors = [d for d in descriptions if any(term in d.lower() for term in ['clean', 'simplify', 'readable', 'maintainable', 'quality', 'standard'])]
        if quality_refactors:
            refactor_categories["Code Quality"] = f"Enhanced code quality with {len(quality_refactors)} refactoring improvements focusing on readability, maintainability, and coding standards."
        
        # API & Interface Design
        api_refactors = [d for d in descriptions if any(term in d.lower() for term in ['api', 'interface', 'method', 'function', 'signature', 'endpoint'])]
        if api_refactors:
            refactor_categories["API Design"] = f"Refined API design through {len(api_refactors)} interface improvements, method restructuring, and endpoint optimization."
        
        # Dependency & Import Management
        dep_refactors = [d for d in descriptions if any(term in d.lower() for term in ['dependency', 'import', 'package', 'module', 'library', 'external'])]
        if dep_refactors:
            refactor_categories["Dependency Management"] = f"Improved dependency management with {len(dep_refactors)} refactoring changes to imports, packages, and external library usage."
        
        # Build comprehensive summary
        improvement_text = "improvement" if count == 1 else "improvements"
        summary_parts = [f"Extensive codebase refactoring with {count} {improvement_text} enhancing code quality and maintainability:"]
        
        for category_name, category_desc in refactor_categories.items():
            summary_parts.append(f"\n• **{category_name}**: {category_desc}")
        
        if not refactor_categories:
            # Fallback for unrecognized patterns
            summary_parts.append(f"\n• **General Refactoring**: Improved code organization, maintainability, and architectural design through systematic refactoring efforts.")
        
        summary_parts.append(f"\n\nThese refactoring efforts result in cleaner, more maintainable code that is easier to understand, modify, and extend while improving overall system architecture.")
        
        return "".join(summary_parts)

    def _summarize_tests(self, descriptions: List[str], key_terms: List[str]) -> str:
        """Create summary for test commits."""
        count = len(descriptions)
        if count == 0:
            return ""
            
        return f"Enhanced testing suite with {count} additions including new test cases, improved coverage, and testing infrastructure updates."

    def _summarize_performance(self, descriptions: List[str], key_terms: List[str]) -> str:
        """Create summary for performance commits."""
        count = len(descriptions)
        if count == 0:
            return ""
            
        return f"Optimized performance with {count} improvements targeting speed, efficiency, and resource utilization."

    def _summarize_general(self, commit_type: str, descriptions: List[str], key_terms: List[str]) -> str:
        """Create summary for other commit types."""
        count = len(descriptions)
        if count == 0:
            return ""
            
        return f"Made {count} {commit_type} changes improving various aspects of the project."