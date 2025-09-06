import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import List, Iterator

from llama_cpp import Llama, CreateCompletionResponse
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn

# --- Model and Prompt Configuration ---
MODEL_REPO = "bartowski/deepseek-ai_DeepSeek-R1-0528-Qwen3-8B-GGUF"
MODEL_FILE = "deepseek-ai_DeepSeek-R1-0528-Qwen3-8B-Q4_K_M.gguf"
MODEL_DOWNLOAD_URL = f"https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}"

MODELS_DIR = Path.home() / ".preflight" / "models"
MODEL_PATH = MODELS_DIR / MODEL_FILE

# Load the system prompt from the packaged data file
try:
    SYSTEM_PROMPT = resources.files('preflight').joinpath('system_prompt.txt').read_text(encoding='utf-8')
except (FileNotFoundError, ModuleNotFoundError):
    print("FATAL: Could not find system_prompt.txt within the preflight package.", file=sys.stderr)
    sys.exit(1)

# --- Data Classes for Type-Safe JSON Parsing ---
@dataclass
class LineRange:
    start: int
    end: int

@dataclass
class ReviewIssue:
    file: str
    line: LineRange
    severity: str
    description: str
    suggestion: str
    codeSnippet: str

    @classmethod
    def from_dict(cls, data: dict) -> 'ReviewIssue':
        data["line"] = LineRange(**data["line"])
        return cls(**data)

# --- Model Management ---
def _download_model():
    """Downloads the model file with a progress bar."""
    print(f"Model not found. Downloading from {MODEL_DOWNLOAD_URL} to {MODEL_PATH}...", file=sys.stderr)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with urllib.request.urlopen(MODEL_DOWNLOAD_URL) as response:
            total_size = int(response.headers.get('content-length', 0))
            with Progress(
                TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                DownloadColumn(),
                "•",
                TransferSpeedColumn(),
            ) as progress:
                task = progress.add_task("Downloading", total=total_size, filename=MODEL_FILE)
                with open(MODEL_PATH, 'wb') as f:
                    while chunk := response.read(1024):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))
        print(f"Model downloaded successfully to {MODEL_PATH}", file=sys.stderr)
    except Exception as e:
        print(f"Failed to download model: {e}", file=sys.stderr)
        if MODEL_PATH.exists():
            MODEL_PATH.unlink() # Clean up partial download
        raise

def get_model() -> Llama:
    """Ensures the model is available and returns a Llama instance."""
    if not MODEL_PATH.exists():
        _download_model()

    return Llama(model_path=str(MODEL_PATH), n_ctx=32768, n_gpu_layers=-1, n_batch=2048)

# --- AI Analysis ---
def analyze_diff(diff_content: str, model: Llama) -> CreateCompletionResponse | Iterator[CreateCompletionResponse]:
    """Analyzes a git diff using the AI model and streams the response.

    Returns:
        A generator that yields response chunks.
    """
    user_prompt = f"""Analyze the following git diff:

<diff>
{diff_content}
</diff>"""
    prompt = f"<｜begin of sentence｜>{SYSTEM_PROMPT}<｜User｜>{user_prompt}<｜Assistant｜>"

    return model(
        prompt,
        max_tokens=0, # 0 = unlimited generation within context window
        temperature=0.7,
        echo=False,
        stream=True
    )

