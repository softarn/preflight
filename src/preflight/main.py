import json
from importlib import resources
from typing import Iterator
from pathlib import Path

import rich.status
import typer
from llama_cpp import CreateCompletionResponse
from rich.console import Console

from preflight.ai_reviewer import analyze_diff, ReviewIssue, AiModelError
from preflight.display_utils import get_color
from preflight.git_utils import get_git_diff, get_current_branch, get_current_git_diff, get_last_commit_changes, get_current_commit_hash
from preflight.issue_display import IssueDisplay
from preflight.database import Database
from preflight.notification import send_notification
from preflight.report_generator import generate_mock_report

app = typer.Typer()
console = Console()
issue_display = IssueDisplay(console)

@app.callback(invoke_without_command=True)
def review(
    ctx: typer.Context,
    action: str = typer.Argument(
        "commit",
        help="Subcommand to run: commit, diff or branch"
    ),
    base_branch: str = typer.Option(
        "master",
        "--base", "-b",
        help="The base branch to compare against. Not used if --diff is specified."
    ),
    test: bool = typer.Option(
        True,
        "--test",
        help="Uses a test diff to review"
    ),
    mock_ai: bool = typer.Option(
        False,
        "--mock-ai",
        help="Mocks the AI response using test-response.txt"
    )
):
    """Analyzes the files in a git branch for potential issues using a local AI model."""
    try:

        diff_content, commit_hash = get_text_to_review(base_branch, action, test)

        if not diff_content.strip():
            console.print("No differences found. Nothing to review.", style="green")
            return

        # 2. Get AI Model
        console.print(":robot: Loading AI model... (this may take a moment)", style="yellow")

        # 3. Run Analysis and Stream Output
        try:
            result = analyze_diff(diff_content, mock=mock_ai)
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
                
                # Initialize Database
                db = Database()
                saved_count = 0
                
                # Save issues to database
                for item in issues_data:
                    issue = ReviewIssue.from_dict(item)
                    db.save_issue(issue, commit_hash)
                    saved_count += 1
                
                db.close()
                console.print(f"✨ Analysis complete. Saved {saved_count} issues to database.", style="bold green")
                
                # Generate report and notify
                report_path = Path.home() / ".preflight" / "report.html"
                generate_mock_report(report_path)
                
                if saved_count > 0:
                    send_notification(f"Found {saved_count} issues in review", f"file://{report_path}")
                else:
                    send_notification("No issues found in review", f"file://{report_path}")
                
            except json.JSONDecodeError as e:
                console.print(f":x: Failed to parse JSON from AI response: {e}", style="bold red")
                console.print(f"--- Extracted Text ---\n{json_text}", style="dim")
                raise typer.Exit(code=1)
        else:
            console.print(":warning: Could not find a JSON array in the model's output.", style="yellow")
            console.print(f"--- Raw Response ---\n{full_response}", style="dim")

    except FileNotFoundError:
        console.print(":x: Critical Error: 'git' command not found. Is Git installed?", style="bold red")
        raise typer.Exit(code=1)
    except Exception:
        console.print(":x: An unexpected error occurred.", style="bold red")
        console.print_exception(show_locals=True)
        raise typer.Exit(code=1)


def get_text_to_review(base_branch: str, action: str, test: bool) -> tuple[str, str]:
    if test:
        return resources.files('preflight').joinpath('test_diff.txt').read_text(encoding='utf-8'), "TEST_COMMIT_HASH"

    if action == 'commit':
        return get_last_commit_changes(), get_current_commit_hash()

    raise NotImplemented("Only commits reviews are implemented")

    # if type == 'diff':
    #     console.print(":mag: Analyzing current Git diff...", style="yellow")
    #     diff_content = get_current_git_diff()
    # else:
    #     console.print(f":mag: Analyzing diff for current branch '{branch}' against {base_branch}...",
    #                   style="yellow")
    #     diff_content = get_git_diff(branch, base_branch)
    # return diff_content


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
