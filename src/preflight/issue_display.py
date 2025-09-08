from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from dataclasses import dataclass

from preflight.ai_reviewer import ReviewIssue  # Import necessary classes
from preflight.display_utils import get_color


@dataclass
class DisplayIssue:
    issue: ReviewIssue
    watched: bool = False


class IssueDisplay:
    def __init__(self, console: Console):
        self.console = console
        self.issues: list[DisplayIssue] = []

    def add_issue(self, issue: ReviewIssue):
        self.issues.append(DisplayIssue(issue=issue, watched=False))

    def update_display(self):
        """Updates the display with the current issue."""
        if not self.issues:
            self.console.print("No issues to display yet.", style="yellow")
            return

        self.console.clear()
        display_issue = self.issues[self.current_issue_index]
        display_issue.watched = True
        issue = display_issue.issue

        unwatched_count = sum(1 for di in self.issues if not di.watched)
        unwatched_color = "green" if unwatched_count == 0 else "red"
        title = f"Preflight Review Issue {self.current_issue_index + 1} of {len(self.issues)} ([{unwatched_color}]Unwatched: {unwatched_count}[/{unwatched_color}])"
        
        severity_style = get_color(issue.severity)

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

        self.current_issue_index = 0

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
