from __future__ import annotations

import os

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

from genacademy_coach.web.gradio_app import launch

if __name__ == "__main__":
    launch()
