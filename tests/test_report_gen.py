import sys
from unittest.mock import MagicMock
sys.modules["llama_cpp"] = MagicMock()
sys.modules["llama_cpp.llama_types"] = MagicMock()

from pathlib import Path
from preflight.ai_reviewer import ReviewIssue, LineRange
from preflight.report_generator import generate_mock_report

def test_report_generation():
    issues = [
        ReviewIssue(
            file="src/main.py",
            line=LineRange(10, 15),
            severity="HIGH",
            description="This is a critical security vulnerability.",
            suggestion="Use a safer function.",
            codeSnippet="def malicious_code():\n    eval(user_input)"
        ),
        ReviewIssue(
            file="src/utils.py",
            line=LineRange(5, 5),
            severity="MEDIUM",
            description="This function is deprecated.",
            suggestion="Use the new API.",
            codeSnippet=None
        ),
        ReviewIssue(
            file="README.md",
            line=LineRange(1, 1),
            severity="LOW",
            description="Typo in documentation.",
            suggestion="Fix typo.",
            codeSnippet="# Preeflight"
        )
    ]
    
    output_path = Path("test_report.html").absolute()
    generate_mock_report(
        path=output_path,
        issues=issues,
        commit_hash="abc1234",
        branch="feature/test-report",
        project="preflight-test"
    )
    
    print(f"Report generated at: {output_path}")
    
    if output_path.exists():
        content = output_path.read_text()
        assert "src/main.py" in content
        assert "severity-HIGH" in content
        assert "This is a critical security vulnerability" in content
        print("Verification successful: File created and contains expected content.")
    else:
        print("Verification failed: File not created.")

if __name__ == "__main__":
    test_report_generation()
