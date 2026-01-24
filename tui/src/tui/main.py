"""Entry point for the TUI application."""

from .app import ViconTUI


def main() -> None:
    app = ViconTUI()
    app.run()


if __name__ == "__main__":
    main()
