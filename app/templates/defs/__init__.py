"""
Template definitions — one file per template, each exporting `TEMPLATE: TemplateDefinition`.

Files are loaded lazily by app/templates/loader.py via importlib. Don't import
from this package directly — go through the loader so the audit snapshot and
caching work correctly.
"""
