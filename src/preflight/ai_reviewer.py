import sys
import urllib.request
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterator, Union, Optional

from llama_cpp import Llama, LlamaTokenizer
from llama_cpp.llama_types import CreateCompletionResponse
from rich.progress import Progress, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn

# --- Model and Prompt Configuration ---
# MODEL_REPO = "bartowski/deepseek-ai_DeepSeek-R1-0528-Qwen3-8B-GGUF"
# MODEL_FILE = "deepseek-ai_DeepSeek-R1-0528-Qwen3-8B-Q4_K_M.gguf"

# MODEL_REPO = "unsloth/Qwen3-30B-A3B-Thinking-2507-GGUF"
# MODEL_FILE = "Qwen3-30B-A3B-Thinking-2507-Q4_K_M.gguf"

# MODEL_REPO = "unsloth/Qwen3-4B-Thinking-2507-GGUF"
# MODEL_FILE = "Qwen3-4B-Thinking-2507-Q2_K.gguf"

# Fast, small and good it seems
# MODEL_REPO = "unsloth/Qwen3-4B-Instruct-2507-GGUF"
# MODEL_FILE = "Qwen3-4B-Instruct-2507-Q3_K_M.gguf"

# Large and good, better than the smaller one
MODEL_REPO = "unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF"
MODEL_FILE = "Qwen3-30B-A3B-Instruct-2507-Q3_K_M.gguf"

# Untested but interesting, needs some fixes first to run properly
# MODEL_REPO = "unsloth/gpt-oss-20b-GGUF"
# MODEL_FILE = "gpt-oss-20b-Q3_K_M.gguf"


# Did not find as many problems as others
# MODEL_REPO = "unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF"
# MODEL_FILE = "Qwen3-Coder-30B-A3B-Instruct-Q3_K_M.gguf"
MODEL_DOWNLOAD_URL = f"https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}"

MODEL_MAX_TOKENS = 262144
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
    codeSnippet: Optional[str] = None

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
            MODEL_PATH.unlink()  # Clean up partial download
        raise


def calculate_tokens(content: str) -> int:
    # This way of counting tokens can probably be optimized a lot so we don't have to load the model
    llama = Llama(model_path=str(MODEL_PATH), n_ctx=1, n_gpu_layers=-1, verbose=False)
    input_tokens = LlamaTokenizer(llama).tokenize(content.encode('utf-8'))
    buffer_for_output = 4096
    return len(input_tokens) + buffer_for_output


def get_model(content: str) -> Llama:
    """Ensures the model is available and returns a Llama instance."""
    if not MODEL_PATH.exists():
        _download_model()

    num_of_tokens = calculate_tokens(content)
    print(f"Calculated tokens to: {num_of_tokens}")

    if num_of_tokens > MODEL_MAX_TOKENS:
        raise AiModelError(f"Input too large for model context window of {MODEL_MAX_TOKENS} tokens.")


    return Llama(model_path=str(MODEL_PATH), n_ctx=num_of_tokens, n_gpu_layers=-1, verbose=False)


# --- AI Analysis ---
def analyze_diff(diff_content: str) -> Union[
    CreateCompletionResponse, Iterator[CreateCompletionResponse]]:
    """Analyzes a git diff using the AI model and streams the response.

    Returns:
        A generator that yields response chunks.
    """
    prompt = get_prompt(diff_content)
    model = get_model(prompt)

    return model(
        prompt,
        max_tokens=0,
        temperature=0.7,
        min_p=0.00,
        top_k=20,
        top_p=0.8,
        repeat_penalty=1.05,
        stream=True,
    )


def get_prompt(diff_content: str) -> str:
    user_prompt = f"""Analyze the following git diff:
    <diff>
{diff_content}
</diff>"""
    prompt = (
        f"<|im_start|>system\n"
        f"{SYSTEM_PROMPT}<|im_end|>\n"
        f"<|im_start|>user\n"
        f"{user_prompt}<|im_end|>\n"
        f"<|im_start|>assistant"
    )
    return prompt

class AiModelError(Exception):
    pass
