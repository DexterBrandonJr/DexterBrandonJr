"""upscayl-wrap: drive Upscayl's upscaling engine from the command line.

Upscayl is a desktop application that upscales photographs with a neural
network, the same idea a game uses to render at a lower resolution and
reconstruct a sharper frame. It ships its engine as a private command-line
binary inside its application bundle. This package drives that binary
directly, and adds the parts a desktop application has no reason to have: a
record of every job, rules that refuse the jobs that would hurt, a prediction
written down before each run and scored after it, and a scheduled sweep of a
watch folder.

Start with ``upscayl-wrap doctor``.
"""

from .config import VERSION  # noqa: F401

__version__ = VERSION
__all__ = ["VERSION", "__version__"]
