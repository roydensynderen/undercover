"""Work the claims queue: uv run -m agent, or uv run -m agent CLM-1001"""

import sys

from agent.main import work

if __name__ == "__main__":
    work(sys.argv[1:])
