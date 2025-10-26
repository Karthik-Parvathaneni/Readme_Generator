from flask import Flask, render_template, request, jsonify
from readme_generator.generator import ReadmeGenerator
from readme_generator.fetcher import GitHubFetcher
from readme_generator.summarizer import CommitSummarizer
from readme_generator.code_analyzer import CodeAnalyzer
import logging
import os

try:
    import nltk
except Exception:
    nltk = None

app = Flask(__name__)

# Setup logging similar to main.py
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("readme-generator")

@app.route('/')
def home():
    # Check NLTK availability on startup
    if nltk is None:
        return render_template('index.html', error="NLTK is required. Install with `pip install nltk` and run `python -m nltk.downloader punkt stopwords`")
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

def _parse_repo_input(text: str):
    """Accept 'owner/repo' or full GitHub url and return (owner, repo)."""
    if not text:
        return None, None
    text = text.strip()
    if text.startswith("http"):
        parts = text.rstrip("/").split("/")
        if len(parts) >= 2:
            return parts[-2], parts[-1]
    if "/" in text:
        owner, repo = text.split("/", 1)
        return owner.strip(), repo.strip()
    return None, None

@app.route('/run', methods=['POST'])
def run_code():
    data = request.get_json()
    repo_input = data.get('user_input', '').strip()
    token = data.get('token') or os.environ.get('GITHUB_TOKEN')
    use_gemini = data.get('use_gemini', False)
    owner, repo = _parse_repo_input(repo_input)
    
    if not owner or not repo:
        return jsonify({'error': 'Invalid repository input. Use owner/repo or full GitHub URL.'}), 400

    try:
        logger.info("Starting README generation for %s/%s", owner, repo)

        # Initialize components
        fetcher = GitHubFetcher(token=token)
        summarizer = CommitSummarizer(use_gemini=use_gemini)
        generator = ReadmeGenerator(include_commit_examples=True)
        # code_analyzer = CodeAnalyzer()

        # Fetch repository data
        logger.info("Fetching repository metadata...")
        meta = fetcher.fetch_repo_meta(owner, repo)

        logger.info("Fetching commit history...")
        commits = fetcher.fetch_commits(owner, repo, max_commits=300)

        if not commits:
            return jsonify({'error': f'No commits found for repository {owner}/{repo}'}), 404

        # Generate commit summaries
        logger.info("Analyzing and summarizing %d commits...", len(commits))
        summaries = summarizer.summarize(commits)

        # Analyze code (optional)
        # try:
        #     logger.info("Analyzing repository code...")
        #     code_docs = code_analyzer.analyze(token, owner, repo)
        # except Exception as e:
        #     logger.warning("Code analysis failed: %s", e)
        #     code_docs = None

        # Generate README
        logger.info("Generating README markdown...")
        # md = generator.generate_markdown(
        #     meta=meta,
        #     summaries=summaries,
        #     commits=commits,
        #     code_docs=code_docs
        # )

        md = generator.generate_markdown(meta, summaries, commits)

        logger.info("README generation completed successfully")
        return jsonify({
            'output': md,
            'stats': {
                'commits_analyzed': len(commits),
                'categories': list(summaries.keys()) if summaries else []
            }
        })

    except RuntimeError as e:
        msg = str(e)
        if 'rate limit' in msg.lower() or 'rate limited' in msg.lower() or '403' in msg:
            return jsonify({
                'error': 'GitHub rate limit exceeded. Provide a personal access token (GITHUB_TOKEN) in the UI or as an environment variable, or try again after the rate limit resets.'
            }), 429
        return jsonify({'error': f'Generation failed: {e}'}), 500
    except Exception as e:
        logger.error("README generation failed: %s", e)
        return jsonify({'error': f'Generation failed: {e}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
