"""Settings, and finding the pieces of Upscayl on disk.

Discovery is deliberately forgiving. Upscayl is a desktop app that ships its
upscaling engine as a private binary inside its application bundle, and both
the binary's name and its exact location inside that bundle have changed
between releases. Hard-coding one path would make this tool break on an
Upscayl update for no good reason, so instead it searches a list of known
locations and reports every place it looked when it comes up empty.

Precedence, highest first:

1. Environment variable — ``UPSCAYL_BIN``, ``UPSCAYL_MODELS``.
2. The config file, ``~/.config/upscayl-wrap/config.json``.
3. Known install locations.
4. ``PATH``.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

VERSION = "0.1.0"
APP_NAME = "upscayl-wrap"

# Names the upscaling engine has shipped under. Checked in order.
BINARY_NAMES = (
    "upscayl-bin",
    "upscayl",
    "upscayl-ncnn",
    "realesrgan-ncnn-vulkan",
)

# Application bundles to look inside, in order of likelihood.
BUNDLE_ROOTS = (
    "/Applications/Upscayl.app",
    "~/Applications/Upscayl.app",
    "/Applications/Setapp/Upscayl.app",
    "/opt/homebrew/Caskroom/upscayl",
)

# Places inside a bundle where the engine and its models have lived.
#
# Both spellings of "resources" are listed on purpose. Upscayl's packaging
# config writes to ``Contents/resources`` while its own runtime code reads
# from ``Contents/Resources``; those are the same directory only because a Mac
# is normally formatted case-insensitively. On a case-sensitive volume they
# are two different places, and only one of them exists.
BUNDLE_BIN_SUBPATHS = (
    "Contents/Resources/bin",
    "Contents/resources/bin",
    "Contents/Resources/resources/bin",
    "Contents/Resources/app.asar.unpacked/resources/bin",
    "Contents/MacOS",
    "Contents/Resources",
)
BUNDLE_MODEL_SUBPATHS = (
    "Contents/Resources/models",
    "Contents/resources/models",
    "Contents/Resources/resources/models",
    "Contents/Resources/app.asar.unpacked/resources/models",
)

# Standalone installs: the engine without the desktop application. The first
# is where this tool's own installer puts it; the second belongs to a
# third-party command-line wrapper that some people already have.
STANDALONE_DIRS = (
    "~/.local/share/upscayl-wrap/engine",
    "~/.upscayl-cli/bin",
    "~/.upscayl-cli",
)

# Where a user drops extra models they downloaded themselves.
EXTRA_MODEL_DIRS = (
    "~/Library/Application Support/Upscayl/models",
    "~/.config/upscayl-wrap/models",
    "~/.local/share/upscayl-wrap/engine/models",
    "~/.upscayl-cli/models",
)

# The order here is not tidiness, it is a bug being mirrored deliberately.
# The engine decides a model's scale by searching its NAME for these tokens in
# exactly this order and taking the first hit. Because it tests "x1" before
# "x16", and "x16" contains "x1", a model called something-x16 is read by the
# engine as scale 1. Matching its order means this tool predicts what the
# engine will actually do rather than what the name appears to say.
_ENGINE_SCALE_TOKENS = (
    (1, ("x1", "1x")),
    (2, ("x2", "2x")),
    (3, ("x3", "3x")),
    (4, ("x4", "4x")),
    (8, ("x8", "8x")),
    (16, ("x16", "16x")),
)


def _expand(path: str) -> str:
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))


@dataclass
class Paths:
    """Everywhere this tool keeps state. One place, so nothing is orphaned."""

    config_dir: str
    config_file: str
    data_dir: str
    ledger: str
    reviews_dir: str
    state_file: str
    halt_file: str
    log_dir: str
    default_inbox: str
    default_outbox: str
    quarantine_dir: str

    def ensure(self) -> None:
        for directory in (
            self.config_dir,
            self.data_dir,
            self.reviews_dir,
            self.log_dir,
        ):
            os.makedirs(directory, exist_ok=True)


def paths() -> Paths:
    config_home = os.environ.get("XDG_CONFIG_HOME") or "~/.config"
    data_home = os.environ.get("XDG_DATA_HOME") or "~/.local/share"
    config_dir = _expand(os.path.join(config_home, APP_NAME))
    data_dir = _expand(os.path.join(data_home, APP_NAME))
    return Paths(
        config_dir=config_dir,
        config_file=os.path.join(config_dir, "config.json"),
        data_dir=data_dir,
        ledger=os.path.join(data_dir, "ledger.jsonl"),
        reviews_dir=os.path.join(data_dir, "reviews"),
        state_file=os.path.join(data_dir, "state.json"),
        halt_file=os.path.join(data_dir, "HALT"),
        log_dir=os.path.join(data_dir, "logs"),
        default_inbox=_expand("~/Pictures/Upscayl Inbox"),
        default_outbox=_expand("~/Pictures/Upscayl Out"),
        quarantine_dir=os.path.join(data_dir, "quarantine"),
    )


@dataclass
class Model:
    """One ncnn model: a pair of files that must both be present."""

    name: str
    directory: str
    native_scale: Optional[int] = None
    has_param: bool = False
    has_bin: bool = False

    @property
    def usable(self) -> bool:
        return self.has_param and self.has_bin

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "directory": self.directory,
            "native_scale": self.native_scale,
            "usable": self.usable,
        }


def native_scale_of(model_name: str) -> Optional[int]:
    """Work out what scale the engine will decide this model is.

    This deliberately reproduces the engine's own logic, including where that
    logic is wrong. It searches the model's name for a scale token and takes
    the first match in a fixed order that tests "x1" before "x16" — so a model
    named ``something-x16`` is treated as scale 1 by the engine, and therefore
    reported as scale 1 here.

    Reporting the true intent instead would be worse than useless: the
    prediction would disagree with the engine on every job, and the scorer
    would raise a false alarm every time. What this needs to answer is not
    "what does the name mean" but "what is about to happen".

    Returns None when the name carries no token at all, which the gate treats
    as "cannot verify" rather than "any scale is fine". All seven models that
    ship end in -4x, so in practice this is always 4.
    """
    lowered = model_name.lower()
    for value, tokens in _ENGINE_SCALE_TOKENS:
        if any(token in lowered for token in tokens):
            return value
    return None


@dataclass
class Config:
    """User settings. Every field has a working default."""

    bin_path: Optional[str] = None
    models_dir: Optional[str] = None
    default_model: Optional[str] = None
    default_scale: int = 4
    output_format: str = "png"
    # 0 lets the engine choose, but its automatic choice is capped at 200
    # however much memory the machine has, which leaves a large graphics
    # processor idle. See suggested_tile_size().
    tile_size: int = 0
    # How many times to retry at half the tile size when the graphics
    # processor runs out of memory or is reset.
    tile_retry_attempts: int = 2
    gpu_id: Optional[int] = None  # None lets the engine choose.
    jobs: int = 1                 # Upscaling is GPU-bound; parallelism hurts.
    out_dir: Optional[str] = None
    inbox_dir: Optional[str] = None
    # Refuse any job whose predicted output exceeds this many megapixels.
    max_output_megapixels: float = 400.0
    # Refuse to start if the predicted output would leave less than this much
    # free disk, in megabytes.
    min_free_disk_mb: int = 2048
    # Autonomy stage: 1 approve everything, 2 adjust within approved, 3 act alone.
    stage: int = 1
    # Consecutive failures that trip the halt and drop back to stage 1.
    failure_halt_threshold: int = 3
    # Run the cheap non-artificial-intelligence baseline on every Nth job so
    # there is something to compare against. 0 disables it.
    counterfactual_every: int = 10
    timeout_seconds: int = 1800
    keep_going_on_error: bool = True

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> "Config":
        target = config_file or paths().config_file
        config = cls()
        if os.path.isfile(target):
            try:
                with open(target, "r", encoding="utf-8") as handle:
                    raw = json.load(handle)
            except (OSError, ValueError):
                # A corrupt config must not brick the tool. Defaults win and
                # `doctor` reports the problem.
                raw = {}
            known = {f for f in cls().__dict__}
            for key, value in raw.items():
                if key in known:
                    setattr(config, key, value)
        config.apply_environment()
        return config

    def apply_environment(self) -> None:
        env_bin = os.environ.get("UPSCAYL_BIN")
        if env_bin:
            self.bin_path = _expand(env_bin)
        env_models = os.environ.get("UPSCAYL_MODELS")
        if env_models:
            self.models_dir = _expand(env_models)

    def save(self, config_file: Optional[str] = None) -> str:
        target = config_file or paths().config_file
        os.makedirs(os.path.dirname(target), exist_ok=True)
        # Write then rename, so an interrupted save cannot leave a half file.
        temporary = target + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(asdict(self), handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, target)
        return target


def total_memory_bytes() -> Optional[int]:
    """Physical memory, from the standard library alone."""
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        return None


def suggested_tile_size(memory_bytes: Optional[int] = None) -> int:
    """A starting tile size, since the engine's own choice does not scale.

    The engine picks its tile size from a four-step ladder that stops at 200,
    and takes the top step for anything above roughly two gigabytes of
    graphics memory. A machine with sixty-four gigabytes therefore gets
    exactly the same tile as one with four, and spends most of the job not
    using the hardware it has.

    These numbers are a deliberate starting point, not a measurement: the
    relationship between tile size and memory used is known to be roughly
    quadratic, but the constant depends on the model and the driver. The
    runner walks this figure back down on its own if the graphics processor
    complains, so guessing a little high costs one retry and guessing low
    costs the whole job's speed.
    """
    if memory_bytes is None:
        memory_bytes = total_memory_bytes()
    if not memory_bytes:
        return 0  # Let the engine decide; we have nothing better to go on.
    gigabytes = memory_bytes / (1024 ** 3)
    if gigabytes >= 32:
        return 512
    if gigabytes >= 16:
        return 384
    if gigabytes >= 8:
        return 256
    return 0


@dataclass
class Discovery:
    """The result of looking for Upscayl, including where we looked."""

    bin_path: Optional[str] = None
    models_dir: Optional[str] = None
    models: List[Model] = field(default_factory=list)
    searched_bin: List[str] = field(default_factory=list)
    searched_models: List[str] = field(default_factory=list)
    problems: List[str] = field(default_factory=list)

    @property
    def usable_models(self) -> List[Model]:
        return [m for m in self.models if m.usable]

    def model_named(self, name: str) -> Optional[Model]:
        for model in self.models:
            if model.name == name:
                return model
        return None


def _candidate_bin_dirs() -> List[str]:
    directories: List[str] = [_expand(d) for d in STANDALONE_DIRS]
    for root in BUNDLE_ROOTS:
        expanded = _expand(root)
        for sub in BUNDLE_BIN_SUBPATHS:
            directories.append(os.path.join(expanded, sub))
        # Homebrew's cask directory holds a version folder, then the bundle.
        if "Caskroom" in expanded and os.path.isdir(expanded):
            try:
                for entry in sorted(os.listdir(expanded)):
                    bundle = os.path.join(expanded, entry, "Upscayl.app")
                    for sub in BUNDLE_BIN_SUBPATHS:
                        directories.append(os.path.join(bundle, sub))
            except OSError:
                pass
    return directories


def _candidate_model_dirs(bin_path: Optional[str]) -> List[str]:
    directories: List[str] = []
    if bin_path:
        # The models folder usually sits beside the bin folder.
        bin_dir = os.path.dirname(bin_path)
        directories.append(os.path.join(os.path.dirname(bin_dir), "models"))
        directories.append(os.path.join(bin_dir, "models"))
    for root in BUNDLE_ROOTS:
        expanded = _expand(root)
        for sub in BUNDLE_MODEL_SUBPATHS:
            directories.append(os.path.join(expanded, sub))
        if "Caskroom" in expanded and os.path.isdir(expanded):
            try:
                for entry in sorted(os.listdir(expanded)):
                    bundle = os.path.join(expanded, entry, "Upscayl.app")
                    for sub in BUNDLE_MODEL_SUBPATHS:
                        directories.append(os.path.join(bundle, sub))
            except OSError:
                pass
    directories.extend(_expand(d) for d in EXTRA_MODEL_DIRS)
    return directories


def find_binary(config: Config) -> "Discovery":
    """Locate the upscaling engine, recording every path tried."""
    result = Discovery()

    explicit = config.bin_path
    if explicit:
        explicit = _expand(explicit)
        result.searched_bin.append(explicit)
        if os.path.isfile(explicit):
            result.bin_path = explicit
        else:
            result.problems.append(
                "configured binary does not exist: %s" % explicit
            )

    if result.bin_path is None:
        for directory in _candidate_bin_dirs():
            for name in BINARY_NAMES:
                candidate = os.path.join(directory, name)
                result.searched_bin.append(candidate)
                if os.path.isfile(candidate):
                    result.bin_path = candidate
                    break
            if result.bin_path:
                break

    if result.bin_path is None:
        for name in BINARY_NAMES:
            found = shutil.which(name)
            result.searched_bin.append("PATH:%s" % name)
            if found:
                result.bin_path = found
                break

    if result.bin_path and not os.access(result.bin_path, os.X_OK):
        result.problems.append(
            "found the engine at %s but it is not executable — "
            "fix with: chmod +x '%s'" % (result.bin_path, result.bin_path)
        )

    return result


def discover_models(models_dir: str) -> List[Model]:
    """List models in a directory.

    An ncnn model is two files that share a stem: ``NAME.param`` describes the
    network and ``NAME.bin`` holds the weights. One without the other is
    reported as unusable rather than silently skipped, because a half-copied
    model is a confusing failure to debug from the engine's own error message.
    """
    found: Dict[str, Model] = {}
    try:
        entries = sorted(os.listdir(models_dir))
    except OSError:
        return []
    for entry in entries:
        stem, extension = os.path.splitext(entry)
        if extension not in (".param", ".bin"):
            continue
        model = found.get(stem)
        if model is None:
            model = Model(
                name=stem,
                directory=models_dir,
                native_scale=native_scale_of(stem),
            )
            found[stem] = model
        if extension == ".param":
            model.has_param = True
        else:
            model.has_bin = True
    return [found[key] for key in sorted(found)]


def discover(config: Config) -> Discovery:
    """Find the engine and every model available to it."""
    result = find_binary(config)

    explicit_models = config.models_dir
    if explicit_models:
        explicit_models = _expand(explicit_models)
        result.searched_models.append(explicit_models)
        if os.path.isdir(explicit_models):
            result.models_dir = explicit_models
        else:
            result.problems.append(
                "configured models directory does not exist: %s" % explicit_models
            )

    seen = set()
    for directory in _candidate_model_dirs(result.bin_path):
        if directory in seen:
            continue
        seen.add(directory)
        result.searched_models.append(directory)
        models = discover_models(directory)
        if not models:
            continue
        if result.models_dir is None:
            result.models_dir = directory
        # Models from extra directories are additive, but a name already found
        # in the primary directory wins — a user's custom copy should not
        # silently shadow the shipped one under the same name.
        existing = {m.name for m in result.models}
        for model in models:
            if model.name not in existing:
                result.models.append(model)

    if result.models_dir and not result.models:
        result.models = discover_models(result.models_dir)

    broken = [m.name for m in result.models if not m.usable]
    if broken:
        result.problems.append(
            "incomplete model files (need both .param and .bin): %s"
            % ", ".join(sorted(broken))
        )

    result.models.sort(key=lambda m: m.name)
    return result


def pick_default_model(config: Config, discovery: Discovery) -> Optional[Model]:
    """Choose a model when the user did not name one.

    Prefers the configured default, then a model whose name suggests it is the
    general-purpose one, then the first usable model of the requested scale.
    """
    usable = discovery.usable_models
    if not usable:
        return None

    if config.default_model:
        named = discovery.model_named(config.default_model)
        if named and named.usable:
            return named

    preferred_order = (
        "upscayl-standard-4x",
        "upscayl-lite-4x",
        "realesrgan-x4plus",
        "remacri-4x",
        "ultrasharp-4x",
    )
    by_name = {m.name: m for m in usable}
    for name in preferred_order:
        if name in by_name:
            return by_name[name]

    matching_scale = [m for m in usable if m.native_scale == config.default_scale]
    if matching_scale:
        return matching_scale[0]
    return usable[0]
