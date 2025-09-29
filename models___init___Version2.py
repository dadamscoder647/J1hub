"""Compatibility shim for legacy package imports."""

from models import Application, Listing, User, VisaDocument  # noqa: F401

__all__ = ["User", "VisaDocument", "Listing", "Application"]
