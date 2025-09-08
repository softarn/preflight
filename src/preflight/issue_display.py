from collections.abc import Iterator
import json
import re
import sys
import time
from typing import Iterator

from rich.console import Console, Group
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from preflight.ai_reviewer import ReviewIssue, LineRange # Import necessary classes

class IssueDisplay:
    def __init__(self, console: Console):
        self.console = console
        self.issues: list[ReviewIssue] = []
        self.current_issue_index = 0

    def add_issue(self, issue: ReviewIssue):
        self.issues.append(issue)
        # When a new issue is added, we might want to immediately display it
        # or update the current view if the user is already in the display mode.
        # For now, let's just add it. The display logic will be handled by display_issues.
        self.update_display()

    def update_display(self):
        """Updates the display with the current issue."""
        if not self.issues:
            self.console.print("No issues to display yet.", style="yellow")
            return

        self.console.clear()
        issue = self.issues[self.current_issue_index]

        # --- Build Rich Content ---
        title = f"Preflight Review Issue {self.current_issue_index + 1} of {len(self.issues)}"
        
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
            renderables.append(Text(issue.codeSnippet, style="green"))

        content_group = Group(*renderables)

        self.console.print(Panel(content_group, title=title, border_style="green"))
        self.console.print("Press Enter for next, 'p' for previous, 'q' to quit...", style="yellow")

    def display_issues(self):
        """Interactively displays a list of review issues in the console."""
        if not self.issues:
            self.console.print("No issues to display.", style="yellow")
            return

        while True:
            self.update_display()
            # --- Handle User Input ---
            try:
                user_input = input()
                if user_input.lower() == 'q':
                    break
                elif user_input.lower() == 'p':
                    self.current_issue_index = (self.current_issue_index - 1) % len(self.issues)
                else:
                    self.current_issue_index = (self.current_issue_index + 1) % len(self.issues)
            except (KeyboardInterrupt, EOFError):
                break
        self.console.print("--- End of Review ---")

