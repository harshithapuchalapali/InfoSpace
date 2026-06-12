from dataclasses import dataclass
import os


DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "output")


@dataclass
class ScraperConfig:
    timeout: int = 30
    delay: float = 1.0
    max_retries: int = 3
    output_dir: str = DEFAULT_OUTPUT_DIR
    respect_robots: bool = True
    randomize_user_agent: bool = True
    verbose: bool = False
