"""Reading failure out of the engine's output, because its exit code cannot.

``upscayl-bin`` ends its ``main`` with an unconditional success return. Every
early exit it has is in argument parsing, model-directory validation and
graphics-device start-up — all of which happen *before* any image is touched.
Once processing begins, nothing that goes wrong can change the exit status.
The per-image work happens on worker threads whose return values are
discarded, and the function that runs the network has no error return at all.

That produces three failures a wrapper has to tell apart:

* **Nothing written.** The encoder refused. Catching this needs only a check
  that the file exists, which is the easy case.
* **A truncated file.** Caught by checking the image is whole.
* **A complete, structurally valid image full of garbage.** This is the one
  that matters. When the graphics device fails part-way, the half-finished
  buffer is handed to the encoder anyway and written out as a perfectly
  well-formed image — frequently solid black. Nothing about the file is wrong.
  Its size is right, its header is right, it opens in Preview. No amount of
  inspecting the output detects it.

The only evidence of that third case is what the engine printed while it ran.
So this module matches the strings that the engine and the neural-network
library underneath it emit on failure. Upscayl's own desktop application does
the same thing for the same reason — it ignores the exit code entirely and
decides success by searching the error stream for the word "Error".

Everything the engine prints, including its progress and success messages,
goes to the error stream rather than the output stream.
"""

from __future__ import annotations

import re
from typing import List, NamedTuple, Optional


class Fault(NamedTuple):
    """One recognisable way the engine fails."""

    key: str
    pattern: str
    meaning: str
    remedy: str
    # True when a smaller tile size is a plausible fix worth retrying.
    retry_smaller_tile: bool = False


# Ordered most specific first, because the first match is reported.
FAULTS: List[Fault] = [
    Fault(
        key="gpu_out_of_memory",
        pattern=r"vkAllocateMemory failed",
        meaning="the graphics processor ran out of memory",
        remedy="use a smaller tile size, for example --tile 128",
        retry_smaller_tile=True,
    ),
    Fault(
        key="gpu_lost",
        pattern=r"vkQueueSubmit failed|vkWaitForFences failed",
        meaning="the graphics processor stopped responding and was reset, "
        "usually from a piece of work that was too large or too small",
        remedy="use a smaller tile size, for example --tile 128",
        retry_smaller_tile=True,
    ),
    Fault(
        key="no_gpu",
        pattern=r"vkEnumeratePhysicalDevices failed|vkCreateInstance failed|"
        r"no vulkan device|Invalid GPU Device|failed to create instance",
        meaning="no usable graphics device was found",
        remedy="every Apple Silicon Mac can run this, so on one of those it "
        "usually means the engine could not start rather than that the hardware "
        "is unsuitable; check 'upscayl-wrap doctor' and that nothing else is "
        "holding the graphics processor",
    ),
    Fault(
        key="model_unreadable",
        # These are the exact shapes the neural-network library prints, taken
        # from its source rather than guessed. It is worth being precise here:
        # the engine throws away the return codes from loading a model, so
        # when a model file is truncated or corrupt these lines are the only
        # sign that anything went wrong. The network then runs on whatever
        # happened to be in memory and produces a black image under a success
        # banner. A pattern that does not match is the same as no check.
        pattern=r"layer (load_model|load_param|create_pipeline|upload_model) [^\n]*failed"
        r"|ParamDict load_param(_bin)? [^\n]*failed"
        r"|load_model error at layer"
        r"|find_(blob|layer)_index_by_name [^\n]*failed"
        r"|create overwritten layer [^\n]*failed"
        r"|compile spir-v module failed"
        r"|(fopen|_wfopen) [^\n]*failed",
        meaning="a model file could not be read or loaded, so the network never "
        "came up and the output is whatever was left in the buffer — usually "
        "solid black",
        remedy="run 'upscayl-wrap doctor'; a model whose two files are present "
        "but truncated looks fine to a file listing and only fails here",
    ),
    Fault(
        key="write_failed",
        pattern=r"Couldn't write the image",
        meaning="the encoder could not write the output",
        remedy="check the output format and that the destination is writable; "
        "very large images can also exceed the encoder's internal size limit",
    ),
    Fault(
        key="read_failed",
        pattern=r"Couldn't read the image",
        meaning="the input could not be decoded",
        remedy="check the file is a real image and is not damaged",
    ),
    Fault(
        key="bad_model_dir",
        pattern=r"Unknown model dir type",
        meaning="the engine rejected the models directory",
        remedy="the directory's path must contain the word 'models'",
    ),
    Fault(
        key="generic_error",
        pattern=r"🚨 Error:|^Error: ",
        meaning="the engine reported an error",
        remedy="see the message for detail",
    ),
]

_COMPILED = [(fault, re.compile(fault.pattern, re.IGNORECASE | re.MULTILINE)) for fault in FAULTS]

# Messages the engine prints on the error stream that are not failures. They
# are listed so a naive search for the word "Error" does not trip on them, and
# so that a success banner is never mistaken for proof of a good result.
BENIGN_MARKERS = (
    "Upscayled Successfully",
    "Detected scale",
    "Creating directory",
    "has alpha channel",
)


def find_fault(stderr_text: Optional[str]) -> Optional[Fault]:
    """The first recognised failure in the engine's output, if any."""
    if not stderr_text:
        return None
    for fault, pattern in _COMPILED:
        if pattern.search(stderr_text):
            return fault
    return None


def matching_lines(stderr_text: Optional[str], fault: Fault, limit: int = 3) -> List[str]:
    """The actual lines that matched, for the record and for the person."""
    if not stderr_text:
        return []
    pattern = re.compile(fault.pattern, re.IGNORECASE)
    found = [line.strip() for line in stderr_text.splitlines() if pattern.search(line)]
    return found[:limit]


def describe(fault: Fault, stderr_text: Optional[str] = None) -> str:
    """One sentence a person can act on."""
    lines = matching_lines(stderr_text, fault, limit=1)
    detail = (" (%s)" % lines[0][:160]) if lines else ""
    return "%s%s — %s" % (fault.meaning, detail, fault.remedy)


def next_tile_size(current: int, floor: int = 32) -> Optional[int]:
    """Halve the tile size for a retry, or give up.

    The network runs on one tile at a time with a fixed border added around
    each, so the memory a tile needs grows with the square of its size:
    halving the tile roughly quarters the peak. Below the floor the borders
    dominate, the work gets slower rather than smaller, and visible seams
    start appearing in flat areas of the picture.
    """
    if current <= 0:
        # Zero means the engine chooses. Its automatic choice tops out at 200
        # no matter how much memory the machine has, so that is the number a
        # retry has to beat.
        current = 200
    candidate = current // 2
    if candidate < floor:
        return None
    return candidate
