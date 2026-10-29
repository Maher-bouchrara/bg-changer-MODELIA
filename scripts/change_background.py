"""Same as the `bgchange` command, kept so the older command still works.

    uv run python scripts/change_background.py photo.jpg --color "#FF0066"
    is exactly
    uv run bgchange photo.jpg --color "#FF0066"

All the options and the code are in bgchange/cli.py.
"""

from bgchange.cli import main

if __name__ == "__main__":
    main()
