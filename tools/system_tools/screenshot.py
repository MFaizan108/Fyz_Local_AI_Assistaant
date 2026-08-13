from datetime import datetime
from pathlib import Path

from PIL import ImageGrab

SCREENSHOTS_DIR = Path(__file__).resolve().parents[2] / "logs" / "screenshots"


def take_screenshot() -> str:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = SCREENSHOTS_DIR / f"screenshot_{datetime.now():%Y%m%d_%H%M%S}.png"

    image = ImageGrab.grab()
    image.save(filename)

    return f"Screenshot saved to {filename}"
