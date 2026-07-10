"""Starter files for each supported stack.

A preset answers one question: "this stack was declared in project.yaml but its
files don't exist yet -- what should be written?" Presets return plain
``{relative_path: content}`` mappings and never touch the filesystem; deciding
what is missing and writing it is local_mode's job. Existing files are never
overwritten.

Which preset runs for which stack is not decided here: each language's provider
in ``init_configurator.languages`` owns that, so there is exactly one registry
to extend when a language is added.
"""
