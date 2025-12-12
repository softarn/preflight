from pathlib import Path

from preflight.ai_reviewer import ReviewIssue


import os

def generate_mock_report(path: Path, issues: list[ReviewIssue], commit_hash: str, branch: str, project: str, reports_root: Path = None):
    """Generates a mock HTML report at the specified path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if reports_root is None:
        # Fallback if not provided, though main.py should provide it
        reports_root = path.parent
        
    _setup_report_assets(reports_root)
    
    # Calculate relative path for logo
    # report is at 'path', logo is at 'reports_root/img/logo.png'
    logo_abs_path = reports_root / "img" / "logo.png"
    logo_html = ""
    if logo_abs_path.exists():
        rel_logo_path = os.path.relpath(logo_abs_path, path.parent)
        logo_html = f'<img src="{rel_logo_path}" alt="Preflight Logo" class="logo">'

    issues_html = ""
    for issue in issues:
        severity_class = f"severity-{issue.severity}"
        code_block = ""
        if issue.codeSnippet:
            code_block = f"""
            <div class="code-snippet">
                <pre><code>{issue.codeSnippet}</code></pre>
            </div>
            """
            
        issues_html += f"""
        <div class="issue {severity_class}">
            <div class="issue-header">
                <span class="badge {severity_class}">{issue.severity}</span>
                <span class="file-path">{issue.file}:{issue.line.start}</span>
            </div>
            <div class="issue-content">
                <h3>{issue.description}</h3>
                <div class="suggestion">
                    <strong>Suggestion:</strong> {issue.suggestion}
                </div>
                {code_block}
            </div>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Preflight Review - {project}</title>
        <style>
            :root {{
                --bg-color: #f8f9fa;
                --text-color: #333;
                --card-bg: #ffffff;
                --border-color: #e9ecef;
                --high-color: #dc3545;
                --medium-color: #fd7e14;
                --low-color: #28a745;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-color);
                line-height: 1.6;
                margin: 0;
                padding: 40px 20px;
            }}
            
            .container {{
                max-width: 900px;
                margin: 0 auto;
            }}
            
            header {{
                margin-bottom: 40px;
                text-align: center;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 16px;
            }}
            
            .logo {{
                height: 100px;
                width: auto;
            }}
            
            h1 {{
                margin: 0;
                color: #2c3e50;
                font-size: 2.5em;
            }}
            
            .metadata {{
                color: #6c757d;
                font-size: 0.9em;
            }}

            .metadata span {{
                margin: 0 10px;
            }}
            
            .issue {{
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                margin-bottom: 24px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                overflow: hidden;
            }}
            
            .issue:hover {{
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }}
            
            .issue-header {{
                padding: 12px 20px;
                border-bottom: 1px solid var(--border-color);
                display: flex;
                align-items: center;
                gap: 12px;
                background-color: #fafbfc;
            }}
            
            .file-path {{
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
                font-size: 0.9em;
                color: #586069;
            }}
            
            .badge {{
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.75em;
                font-weight: bold;
                color: white;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .badge.severity-HIGH {{ background-color: var(--high-color); }}
            .badge.severity-MEDIUM {{ background-color: var(--medium-color); }}
            .badge.severity-LOW {{ background-color: var(--low-color); }}
            
            .issue.severity-HIGH {{ border-left: 4px solid var(--high-color); }}
            .issue.severity-MEDIUM {{ border-left: 4px solid var(--medium-color); }}
            .issue.severity-LOW {{ border-left: 4px solid var(--low-color); }}
            
            .issue-content {{
                padding: 20px;
            }}
            
            .issue-content h3 {{
                margin-top: 0;
                font-size: 1.1em;
                color: #24292e;
            }}
            
            .suggestion {{
                background-color: #f1f8ff;
                border: 1px solid #c8e1ff;
                border-radius: 4px;
                padding: 12px;
                margin: 16px 0;
                color: #0366d6;
            }}
            
            .code-snippet {{
                background-color: #f6f8fa;
                border: 1px solid #eaecef;
                border-radius: 4px;
                padding: 12px;
                overflow-x: auto;
            }}
            
            pre {{
                margin: 0;
            }}
            
            code {{
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
                font-size: 0.85em;
            }}

            .empty-state {{
                text-align: center;
                padding: 40px;
                color: #6c757d;
                background: white;
                border-radius: 8px;
                border: 1px dashed #dee2e6;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                {logo_html}
                <h1>Review Report</h1>
                <div class="metadata">
                    <span><strong>Project:</strong> {project}</span>
                    <span><strong>Branch:</strong> {branch}</span>
                    <span><strong>Commit:</strong> {commit_hash[:7]}</span>
                </div>
            </header>

            <main>
                {issues_html if issues else '<div class="empty-state">No issues found! Great job! 🎉</div>'}
            </main>
        </div>
    </body>
    </html>
    """
    path.write_text(html_content, encoding="utf-8")

def _setup_report_assets(reports_root: Path) -> None:
    """
    Sets up necessary assets for the report (like images) in the shared assets directory.
    Currently handles copying the logo to reports_root/img/logo.png.
    """
    # Try to find logo in project root (dev mode) or package resources (prod mode logic could go here)
    # For now, assuming dev structure: src/preflight/report_generator.py -> ... -> project_root/img/logo.png
    project_root = Path(__file__).resolve().parent.parent.parent
    logo_source = project_root / "img" / "logo.png"
    
    if logo_source.exists():
        img_dir = reports_root / "img"
        img_dir.mkdir(parents=True, exist_ok=True)
        destination = img_dir / "logo.png"
        
        import shutil
        if not destination.exists():
            shutil.copy(logo_source, destination)
