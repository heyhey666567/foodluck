"""Launch script used by the macOS PyInstaller bundle."""

from foodluck.app import main

if __name__ == "__main__":
    raise SystemExit(main())
