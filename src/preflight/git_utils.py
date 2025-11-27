import subprocess
import sys

def get_current_branch() -> str:
    """Gets the name of the current Git branch."""
    try:
        process = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return process.stdout.strip()
    except FileNotFoundError:
        print("Error: 'git' command not found. Is Git installed and in your PATH?", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as e:
        print(f"Error getting current git branch: {e.stderr}", file=sys.stderr)
        raise

def get_current_commit_hash() -> str:
    """Gets the current git commit hash (HEAD)."""
    try:
        process = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return process.stdout.strip()
    except FileNotFoundError:
        print("Error: 'git' command not found. Is Git installed and in your PATH?", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as e:
        print(f"Error getting current commit hash: {e.stderr}", file=sys.stderr)
        raise

def get_current_git_diff() -> str:
    """Gets the current Git diff (unstaged and staged changes)."""
    try:
        process = subprocess.run(
            ["git", "diff"],
            capture_output=True,
            text=True,
            check=True
        )
        return process.stdout
    except FileNotFoundError:
        print("Error: 'git' command not found. Is Git installed and in your PATH?", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as e:
        print(f"Error getting current git diff: {e.stderr}", file=sys.stderr)
        raise

def get_last_commit_changes() -> str:
    """Gets the diff and metadata for the last git commit (HEAD)."""
    try:
        process = subprocess.run(
            ["git", "show", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return process.stdout
    except FileNotFoundError:
        print("Error: 'git' command not found. Is Git installed and in your PATH?", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as e:
        print("Error getting last commit changes:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        raise

def get_git_diff(branch_name: str, base_branch: str = "master") -> str:
    """Gets the git diff between the specified branch and a base branch.

    Args:
        branch_name: The name of the branch to compare.
        base_branch: The base branch to compare against (defaults to "master").

    Returns:
        The git diff as a string.
    """
    try:
        command = ["git", "diff", base_branch, branch_name]
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return process.stdout
    except FileNotFoundError:
        print("Error: 'git' command not found. Is Git installed and in your PATH?", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as e:
        print(f"Error getting git diff for branch '{branch_name}':", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        raise
