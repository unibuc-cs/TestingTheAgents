"""The eval catalog: scenario tests and dataset items, loaded as ``EvalCase``s, and the catalog of properties
they check, loaded as ``Property``s."""

from .loader import CATALOG_ROOT, EvalCase, Property, load_catalog, load_properties

__all__ = ["CATALOG_ROOT", "EvalCase", "Property", "load_catalog", "load_properties"]
