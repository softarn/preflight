import json
from importlib import resources
from typing import Iterator

import rich.status
import typer
from llama_cpp import CreateCompletionResponse
from rich.console import Console

from preflight.ai_reviewer import analyze_diff, ReviewIssue, AiModelError
from preflight.display_utils import get_color
from preflight.git_utils import get_git_diff, get_current_branch, get_current_git_diff
from preflight.issue_display import IssueDisplay

app = typer.Typer()
console = Console()
issue_display = IssueDisplay(console)


@app.command()
def review(
        branch: str = typer.Argument(
            get_current_branch(),
            help="The git branch to analyze. Defaults to the current branch if not provided. Not used if --diff is specified."
        ),
        base_branch: str = typer.Option(
            "master",
            "--base", "-b",
            help="The base branch to compare against. Not used if --diff is specified."
        ),
        diff: bool = typer.Option(
            False,
            "--diff",
            help="Review the current Git diff (unstaged and staged changes)."
        ),
        test: bool = typer.Option(
            True,
            "--test", help="Uses a test diff to review"
        )
):
    """Analyzes the files in a git branch for potential issues using a local AI model."""
    try:
        diff_content = get_text_to_review(base_branch, branch, diff, test)

        if not diff_content.strip():
            console.print("No differences found. Nothing to review.", style="green")
            return

        # 2. Get AI Model
        console.print(":robot: Loading AI model... (this may take a moment)", style="yellow")

        # 3. Run Analysis and Stream Output
        try:
            result = analyze_diff(diff_content)
        except AiModelError as e:
            console.print(f":x: Critical Error: {e}", style="bold red")
            return

        console.clear()

        spinner = rich.status.Status("Analyzing code...", spinner="dots")

        spinner.start()
        full_response = process_model_output(result, spinner)
        spinner.stop()

        # 4. Parse the final response
        console.print("Parsing final response...", style="yellow")

        # Find the start and end of the JSON array
        start_index = full_response.find('[')
        end_index = full_response.rfind(']')

        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_text = full_response[start_index: end_index + 1]
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
        if not issue_display.issues:  # Check issue_display for issues
            console.print("✨ Analysis complete. No issues found!", style="bold green")
            return

        issue_display.display_issues()  # New: Use IssueDisplay to display issues

    except FileNotFoundError:
        console.print(":x: Critical Error: 'git' command not found. Is Git installed?", style="bold red")
        raise typer.Exit(code=1)
    except Exception:
        console.print(":x: An unexpected error occurred.", style="bold red")
        console.print_exception(show_locals=True)
        raise typer.Exit(code=1)


def get_text_to_review(base_branch: str, branch: str, diff: bool, test: bool) -> str:
    if test:
        return resources.files('preflight').joinpath('test_diff.txt').read_text(encoding='utf-8')

    if diff:
        if branch is not None or base_branch != "master":
            console.print(":x: Cannot use --diff with branch arguments (--branch or --base).", style="bold red")
            raise typer.Exit(code=1)
        console.print(":mag: Analyzing current Git diff...", style="yellow")
        diff_content = get_current_git_diff()
    else:
        console.print(f":mag: Analyzing diff for current branch '{branch}' against {base_branch}...",
                      style="yellow")
        diff_content = get_git_diff(branch, base_branch)
    return diff_content


def process_model_output(result: CreateCompletionResponse | Iterator[CreateCompletionResponse],
                         spinner: rich.status.Status) -> str:
    full_response = ""
    partial_response = ""
    open_brackets = 0
    for output in result:
        output_text = output['choices'][0]['text']

        for output_char in output_text:
            partial_response += output_char

            open_brackets += output_char.count('{')
            open_brackets -= output_char.count('}')

            if open_brackets == 0 and len(partial_response) > 5:
                start_index = partial_response.find('{')
                end_index = partial_response.rfind('}')
                try:
                    # {'file': 'src/main/java/com/example/app/Greeter.java', 'line': {'start': 26, 'end': 26}, 'severity': 'MEDIUM', 'description': "The 'generateGreeting' method uses a new Random instance on each call, which is inefficient and unnecessary. This can
                    # lead to poor performance if called frequently.", 'suggestion': 'Consider reusing a single Random instance as a class-level field or using a thread-safe alternative like ThreadLocalRandom.', 'codeSnippet': 'public String generateGreeting(String
                    # name) {\n        if (new Random().nextBoolean()) {\n            return "Hello, " + name;\n        } else {\n            return "Howdy ho, " + name;\n        }\n    }'}
                    issue_data = json.loads(partial_response[start_index: end_index + 1])
                    color = get_color(issue_data['severity'])

                    spinner.stop()
                    console.print(f"\r:warning: Issue found in {issue_data['file']}\n{issue_data['description']}\n\n", style=color, end="")
                    spinner.start()
                    partial_response = partial_response[end_index + 1:]
                except json.JSONDecodeError:
                    pass

        full_response += output['choices'][0]['text']
    return full_response


if __name__ == "__main__":
    app()
