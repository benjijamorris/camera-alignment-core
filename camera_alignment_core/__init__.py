__author__ = "AICS"

# Do not edit this string manually, always use bumpversion
# Details in CONTRIBUTING.md
__version__ = "1.0.0.dev0"


def get_module_version():
    return __version__


from .align import Align

__all__ = ("Align", "get_module_version")
