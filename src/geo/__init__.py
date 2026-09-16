"""Geography helpers (county FIPS)."""

__all__ = ["County", "load_counties", "lookup_fips", "normalize_fips"]


def __getattr__(name: str):
    if name in __all__:
        from . import fips as _fips

        return getattr(_fips, name)
    raise AttributeError(name)
