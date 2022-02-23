import pkgutil
from collections.abc import Iterator

__version__ = "0.1.0"
__all__ = ("get_package_names",)


def get_package_names() -> Iterator[str]:
    """Iterate names of all packages located in /src/."""
    for package in pkgutil.iter_modules(__path__):
        if package.ispkg:
            yield package.name
