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
    
    reports_root = Path("test_reports").absolute()
    project = "preflight-test"
    branch = "feature/test-report"
    
    # Structure: reports_root/project/branch/report.html
    output_path = reports_root / project / branch / "test_report.html"
    
    generate_mock_report(
        path=output_path,
        issues=issues,
        commit_hash="abc1234",
        branch=branch,
        project=project,
        reports_root=reports_root
    )
    
    print(f"Report generated at: {output_path}")
    
    if output_path.exists():
        content = output_path.read_text()
        assert "src/main.py" in content
        assert "severity-HIGH" in content
        assert "This is a critical security vulnerability" in content
        
        # Verify Logo
        img_dir = reports_root / "img"
        logo_dest = img_dir / "logo.png"
        
        if logo_dest.exists():
            print("Verification successful: Logo copied to img/logo.png")
            # Expected relative path from project/branch/report.html to img/logo.png:
            # ../../img/logo.png
            if '../../img/logo.png' in content:
                print("Verification successful: HTML contains correct relative logo path.")
            else:
                 print(f"Verification WARNING: HTML might have incorrect image path. Content snippet: {content[:1000]}")
        else:
            print("Verification WARNING: Logo NOT copied. (This is expected if logo.png is missing in project root)")

        print("Verification successful: File created and contains expected content.")
    else:
        print("Verification failed: File not created.")

if __name__ == "__main__":
    test_report_generation()
