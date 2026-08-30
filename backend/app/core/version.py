"""The single place the running build names itself.

Both `/health` and the footer in the UI read this, so what an interviewer sees
in the browser is provably the same build as the tag on GitHub.
"""

APP_VERSION = "1.23.2"
