from pathlib import Path

def _read_version():
    """Reads the version from the VERSION file."""
    try:
        # Assuming the VERSION file is in the project root, one level up from 'gui'
        version_path = Path(__file__).parent.parent / "VERSION"
        return version_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "0.0.0-dev"

APP_NAME = "NetPilot"
APP_VERSION = _read_version()
APP_AUTHOR = "Sami Turpeinen"