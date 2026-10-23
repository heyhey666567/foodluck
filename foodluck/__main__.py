"""Allow ``python -m foodluck`` to launch the desktop app."""

from foodluck.app import main

raise SystemExit(main())
