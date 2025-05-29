# Without this file pytest runs into an cyclic import error
from server.app import app  # pragma: no cover
