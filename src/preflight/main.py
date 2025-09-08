from collections.abc import Iterator
import json
import re
import sys
import time
from typing import Iterator

import typer
from rich.console import Console, Group
from rich.panel import Panel

from rich.style import Style
from rich.text import Text

from preflight.ai_reviewer import get_model, analyze_diff, ReviewIssue
from preflight.git_utils import get_git_diff
from preflight.issue_display import IssueDisplay # New import



app = typer.Typer()
console = Console()
issue_display = IssueDisplay(console) # New: Instantiate IssueDisplay




@app.command()
def review(branch: str = typer.Argument(..., help="The git branch to analyze against master.")):
    """Analyzes the files in a git branch for potential issues using a local AI model."""
    total_start_time = time.monotonic()
    load_duration = 0
    analysis_duration = 0
    try:
        # 1. Get Git Diff
        console.print(f":mag: Analyzing diff for branch '{branch}' against master...", style="yellow")
        diff_content = get_git_diff(branch)
        if not diff_content.strip():
            console.print("No differences found. Nothing to review.", style="green")
            return

        # 2. Get AI Model
        console.print(":robot: Loading AI model... (this may take a moment)", style="yellow")
        load_start_time = time.monotonic()
        model = get_model()
        load_duration = time.monotonic() - load_start_time

        # 3. Run Analysis and Stream Output
        analysis_start_time = time.monotonic()
        result = analyze_diff(diff_content, model)

        full_response = ""
        # The analyze_diff function returns an iterator, so we need to consume it
        # to get the full response.
        if isinstance(result, Iterator):
            for output in result:
                full_response += output['choices'][0]['text']
        else:
            # This case should ideally not be hit if analyze_diff always streams
            full_response = result['choices'][0]['text']
        analysis_duration = time.monotonic() - analysis_start_time

        # 4. Parse the final response
        console.print("Parsing final response...", style="yellow")
        
        # Find the start and end of the JSON array
        start_index = full_response.find('[')
        end_index = full_response.rfind(']')

        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_text = full_response[start_index : end_index + 1]
            try:
                issues_data = json.loads(json_text)
                # New: Add issues one by one to IssueDisplay
                for item in issues_data:
                    issue_display.add_issue(ReviewIssue.from_dict(item))
            except json.JSONDecodeError as e:
                console.print(f":x: Failed to parse JSON from AI response: {e}", style="bold red")
                console.print(f"--- Extracted Text ---\n{json_text}", style="dim")
                raise typer.Exit(code=1)
        else:
            console.print(":warning: Could not find a JSON array in the model's output.", style="yellow")
            console.print(f"--- Raw Response ---\n{full_response}", style="dim")
            # If no issues found, ensure issue_display is empty
            issue_display.issues = []

        # 5. Display Results
        if not issue_display.issues: # Check issue_display for issues
            console.print("✨ Analysis complete. No issues found!", style="bold green")
            return

        issue_display.display_issues() # New: Use IssueDisplay to display issues

    except FileNotFoundError:
        console.print(":x: Critical Error: 'git' command not found. Is Git installed?", style="bold red")
        raise typer.Exit(code=1)
    except Exception:
        console.print(":x: An unexpected error occurred.", style="bold red")
        console.print_exception(show_locals=True)
        raise typer.Exit(code=1)
    finally:
        total_duration = time.monotonic() - total_start_time
        console.print(f"[bold]Performance Metrics[/bold]")
        console.print(f"- Model Loading: [cyan]{load_duration:.2f}s[/cyan]")
        console.print(f"- AI Analysis:   [cyan]{analysis_duration:.2f}s[/cyan]")
        console.print(f"- Total Run:     [cyan]{total_duration:.2f}s[/cyan]")

if __name__ == "__main__":
    app()

