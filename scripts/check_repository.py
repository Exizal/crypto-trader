"""Check tracked files before publication; never prints suspected secret values."""

from pathlib import Path
import re
import shutil
import subprocess  # nosec B404
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {".private", "backups", "logs", "data", "work", ".venv", "__pycache__"}
FORBIDDEN_NAMES = {
    "live_state.json",
    "paper_state.json",
    "ui_settings.json",
    "launch-check.json",
    "verification.json",
    ".env",
    "STOP",
}
FORBIDDEN_SUFFIXES = {".exe", ".zip", ".pem", ".key", ".bin", ".pfx", ".p12", ".log", ".pyc"}
PATTERNS = [
    re.compile(x)
    for x in (
        r"sk-(?:proj-)?[A-Za-z0-9_-]{32,}",
        r"gh[pousr]_[A-Za-z0-9]{30,}",
        r"github_pat_[A-Za-z0-9_]{30,}",
        r"AKIA[A-Z0-9]{16}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    )
]


def inspect_file(relative, raw):
    path = Path(relative)
    if (
        set(path.parts) & FORBIDDEN_PARTS
        or path.name in FORBIDDEN_NAMES
        or path.suffix.lower() in FORBIDDEN_SUFFIXES
        or path.name.startswith(".env.")
    ):
        return "Runtime or sensitive file must not be published"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return "Unexpected binary file"
    if any(pattern.search(text) for pattern in PATTERNS):
        return "Potential credential detected; value withheld"
    return None


def main():
    # Fixed Git read operation, no user-controlled arguments and no shell.
    git = shutil.which("git")
    if not git or not Path(git).is_absolute():
        raise RuntimeError("Git executable was not found")
    result = subprocess.run([git, "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)  # nosec B603
    paths = [p for p in result.stdout.decode().split("\0") if p]
    if not paths:
        raise RuntimeError("No tracked files were found to review")
    errors = []
    for relative in paths:
        path = ROOT / relative
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
            errors.append(f"{relative}: links or paths outside the project are not publishable")
            continue
        reason = inspect_file(relative, path.read_bytes())
        if reason:
            errors.append(f"{relative}: {reason}")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Publication check passed for {len(paths)} tracked text files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
