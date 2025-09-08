from collections.abc import Iterator
import json
import re
import sys
import time
from typing import Iterator

import typer
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from preflight.ai_reviewer import get_model, analyze_diff, ReviewIssue
from preflight.git_utils import get_git_diff

LINES_TO_SHOW = 20

app = typer.Typer()
console = Console()


def stream_and_display(stream: Iterator[dict]) -> str:
    """Displays the streaming output in a live-updating panel and returns the full response."""
    full_response = ""
    display_buffer = ""
    live_panel = Panel("", title="[bold yellow]Model Output[/bold yellow]", border_style="blue", height=LINES_TO_SHOW + 2)

    with Live(live_panel, console=console, screen=True, redirect_stderr=False, vertical_overflow="visible") as live:
        for output in stream:
            chunk = output['choices'][0]['text']
            full_response += chunk
            display_buffer += chunk

            # Get the last lines for display
            lines = display_buffer.splitlines()
            lines_to_show = lines[-LINES_TO_SHOW:]

            # Pad with blank lines to fill the panel
            while len(lines_to_show) < LINES_TO_SHOW:
                lines_to_show.insert(0, "")
            
            display_text = "\n".join(lines_to_show)
            live_panel.renderable = Text(display_text)
            live.update(live_panel)
    
    return full_response


def display_issues_paged(issues: list[ReviewIssue]):
    """Interactively displays a list of review issues in the console."""
    current_issue_index = 0
    
    while True:
        console.clear()
        issue = issues[current_issue_index]

        # --- Build Rich Content ---
        title = f"Preflight Review Issue {current_issue_index + 1} of {len(issues)}"
        
        severity_style = {
            "CRITICAL": "bold red",
            "HIGH": "red",
            "MEDIUM": "yellow",
            "LOW": "cyan",
            "INFO": "blue"
        }.get(issue.severity.upper(), "default")

        main_text = Text()
        main_text.append("Severity: ", style="bold magenta")
        main_text.append(issue.severity, style=severity_style)
        main_text.append(f"\nFile: {issue.file}", style="bold")
        main_text.append(f"\nLine: {issue.line.start}-{issue.line.end}")
        main_text.append("\n\nDescription: ", style="bold magenta")
        main_text.append(issue.description)
        main_text.append("\n\nSuggestion: ", style="bold magenta")
        main_text.append(issue.suggestion)

        renderables = [main_text]

        if issue.codeSnippet:
            renderables.append(Text("\nCode Snippet:", style="bold magenta"))
            renderables.append(Panel(Text(issue.codeSnippet), style="green", border_style="dim"))

        content_group = Group(*renderables)

        console.print(Panel(content_group, title=title, border_style="green"))
        console.print("Press Enter for next, 'p' for previous, 'q' to quit...", style="yellow")

        # --- Handle User Input ---
        try:
            user_input = input()
            if user_input.lower() == 'q':
                break
            elif user_input.lower() == 'p':
                current_issue_index = (current_issue_index - 1) % len(issues)
            else:
                current_issue_index = (current_issue_index + 1) % len(issues)
        except (KeyboardInterrupt, EOFError):
            break
    console.print("--- End of Review ---")


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
        console.print(":thought_balloon: Model loaded. Analyzing diff for issues...", style="yellow")
        analysis_start_time = time.monotonic()
        result = analyze_diff(diff_content, model)

        full_response = ""
        if isinstance(result, Iterator):
            full_response = stream_and_display(result)
        else:
            # Handle the non-streaming case, though our code always streams
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
                issues = [ReviewIssue.from_dict(item) for item in issues_data]
            except json.JSONDecodeError as e:
                console.print(f":x: Failed to parse JSON from AI response: {e}", style="bold red")
                console.print(f"--- Extracted Text ---\n{json_text}", style="dim")
                raise typer.Exit(code=1)
        else:
            console.print(":warning: Could not find a JSON array in the model's output.", style="yellow")
            console.print(f"--- Raw Response ---\n{full_response}", style="dim")
            issues = []

        # 5. Display Results
        if not issues:
            console.print("✨ Analysis complete. No issues found!", style="bold green")
            return

        display_issues_paged(issues)

    except FileNotFoundError:
        console.print(":x: Critical Error: 'git' command not found. Is Git installed?", style="bold red")
        raise typer.Exit(code=1)
    except Exception:
        console.print(":x: An unexpected error occurred.", style="bold red")
        console.print_exception(show_locals=True)
        raise typer.Exit(code=1)
    finally:
        total_duration = time.monotonic() - total_start_time
        console.print(
            Panel(
                f"[bold]Performance Metrics[/bold]\n"
                f"- Model Loading: [cyan]{load_duration:.2f}s[/cyan]\n"
                f"- AI Analysis:   [cyan]{analysis_duration:.2f}s[/cyan]\n"
                f"- Total Run:     [cyan]{total_duration:.2f}s[/cyan]",
                title="[dim]Timings[/dim]",
                border_style="dim"
            )
        )

if __name__ == "__main__":
    app()
