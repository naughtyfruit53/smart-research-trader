"""Utility functions."""

import importlib.metadata


def get_version() -> str:
    """Get application version from package metadata."""
    try:
        return importlib.metadata.version("smart-research-trader")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"
