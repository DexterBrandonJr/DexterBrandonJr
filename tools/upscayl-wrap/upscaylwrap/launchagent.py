"""The scheduled loop, as a macOS launch agent.

The sweep runs as a short-lived process on an interval rather than as a
long-running daemon. A process that starts, does one sweep and exits cannot
leak memory, cannot wedge holding a lock, and comes back clean after a reboot
without anyone noticing it went away.

The plist is written with ``plistlib`` rather than assembled as a string,
because a hand-written property list with one unescaped ampersand in a folder
name is invalid, and launchd's complaint about it is not especially clear.

Two scheduling keys are set. ``StartInterval`` runs the sweep every N seconds,
and ``WatchPaths`` runs it immediately when the inbox changes, so dropping a
photo in the folder does not wait for the next tick.
"""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from typing import Any, Dict, List, Optional

LABEL = "com.dexterbrandonjr.upscaylwrap"


def plist_path() -> str:
    return os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)


def is_installed() -> bool:
    return os.path.isfile(plist_path())


def _entry_point() -> List[str]:
    """How to invoke this tool from a context with no shell setup.

    launchd gives the job a minimal environment with no shell profile, so the
    interpreter and the package directory are both spelled out in full rather
    than relying on anything being on the path.
    """
    package_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(package_dir)
    shim = os.path.join(project_dir, "bin", "upscayl-wrap")
    if os.path.isfile(shim) and os.access(shim, os.X_OK):
        return [shim]
    return [sys.executable, "-m", "upscaylwrap"]


def build_plist(
    *,
    inbox: str,
    out_dir: str,
    interval_seconds: int,
    log_dir: str,
) -> Dict[str, Any]:
    package_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(package_dir)
    arguments = _entry_point() + [
        "watch",
        "--inbox", inbox,
        "--out", out_dir,
        "--quiet",
    ]
    return {
        "Label": LABEL,
        "ProgramArguments": arguments,
        "StartInterval": max(60, int(interval_seconds)),
        # Run as soon as something lands in the inbox, not only on the tick.
        "WatchPaths": [inbox],
        # Do not fire during login; the first sweep can wait for the interval.
        "RunAtLoad": False,
        "StandardOutPath": os.path.join(log_dir, "watch.out.log"),
        "StandardErrorPath": os.path.join(log_dir, "watch.err.log"),
        "WorkingDirectory": project_dir,
        # Tell the system this is background work, so it yields to whatever
        # the person at the keyboard is doing.
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "Nice": 5,
        "EnvironmentVariables": {
            "PYTHONPATH": project_dir,
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin",
        },
    }


def _launchctl(arguments: List[str]) -> "tuple[int, str]":
    try:
        completed = subprocess.run(
            ["/bin/launchctl"] + arguments,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return completed.returncode, (completed.stdout or b"").decode("utf-8", "replace").strip()


def install(
    *,
    inbox: str,
    out_dir: str,
    interval_seconds: int = 300,
    log_dir: str,
) -> Dict[str, Any]:
    if sys.platform != "darwin":
        return {
            "ok": False,
            "message": "launch agents are a macOS feature; nothing was installed.",
        }

    target = plist_path()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    document = build_plist(
        inbox=inbox, out_dir=out_dir, interval_seconds=interval_seconds, log_dir=log_dir
    )
    with open(target, "wb") as handle:
        plistlib.dump(document, handle)
    # launchd refuses a job description that anyone but its owner could write,
    # and the file otherwise lands at whatever the shell's umask happens to
    # be. Rewriting an existing plist keeps its old mode too, so this is set
    # explicitly every time rather than only on creation.
    os.chmod(target, 0o644)

    domain = "gui/%d" % os.getuid()
    # Remove any previous copy first; bootstrap refuses to load a label that
    # is already there, and the error reads like a permissions problem.
    _launchctl(["bootout", "%s/%s" % (domain, LABEL)])
    code, output = _launchctl(["bootstrap", domain, target])
    if code != 0:
        # Older systems only understand the previous spelling.
        code, output = _launchctl(["load", "-w", target])

    ok = code == 0
    message = (
        "Scheduled. It sweeps %s every %d seconds and whenever that folder changes.\n"
        "Results go to %s. Logs in %s.\n"
        "Note: the sweep only acts from stage 2 upwards — at stage 1 it reports and does nothing."
        % (inbox, max(60, interval_seconds), out_dir, log_dir)
        if ok
        else "Wrote %s but launchctl refused it: %s" % (target, output)
    )
    return {
        "ok": ok,
        "plist": target,
        "label": LABEL,
        "inbox": inbox,
        "out_dir": out_dir,
        "interval_seconds": max(60, interval_seconds),
        "launchctl_output": output,
        "message": message,
    }


def uninstall() -> Dict[str, Any]:
    target = plist_path()
    domain = "gui/%d" % os.getuid()
    code, output = _launchctl(["bootout", "%s/%s" % (domain, LABEL)])
    if code != 0:
        _launchctl(["unload", "-w", target])
    existed = os.path.isfile(target)
    try:
        os.unlink(target)
    except OSError:
        pass
    return {
        "ok": True,
        "removed": existed,
        "message": "Scheduled sweep removed." if existed else "No scheduled sweep was installed.",
        "launchctl_output": output,
    }


def status() -> Dict[str, Any]:
    code, output = _launchctl(["print", "gui/%d/%s" % (os.getuid(), LABEL)])
    return {"installed": is_installed(), "loaded": code == 0, "detail": output[:2000]}
