"""Test package.

Being a real package lets test modules import the shared factories from
``tests.conftest`` explicitly, instead of relying on pytest putting this
directory on ``sys.path``.
"""
