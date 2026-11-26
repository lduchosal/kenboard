"""Runtime dependency closure of the published package (ken #1241, #1242).

Shared by scripts/guarddog_gate.py and scripts/dep_scorecard.py: both judge what
actually lands on a production host with ``pip install "kenboard[prod,oidc]"``.

- The default group comes from ``pdm export --prod`` — the lock, freshly resolved by
  ``pdm update --update-all`` earlier in publish.sh, i.e. the latest versions prod gets.
- The ``[project.optional-dependencies]`` extras are not in the lock (``oidc`` clashes
  with pdm's truststore, see pyproject.toml): their packages, and recursively their
  unconditional requirements, are pinned to the version installed in the venv when
  there is one, else to the latest release on PyPI.

Dev-only dependencies are out of scope: they never reach a production host.
"""

import json
import re
import ssl
import subprocess
import tomllib
import urllib.request
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PYPROJECT = REPO / "pyproject.toml"
PYPI_JSON = "https://pypi.org/pypi/{name}/json"
TIMEOUT = 20

_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s;\\]+)")
_REQ_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def canonical(name: str) -> str:
    """Normalise a distribution name (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_pins(text: str) -> dict[str, str]:
    """Parse ``name==version`` lines of a requirements export into a dict."""
    pins: dict[str, str] = {}
    for line in text.splitlines():
        match = _PIN.match(line.strip())
        if match:
            pins[canonical(match.group(1))] = match.group(2)
    return pins


def unconditional_requirements(requires_dist: list[str] | None) -> list[str]:
    """Return the names of requirements that are not behind an ``extra`` marker."""
    names = []
    for req in requires_dist or []:
        if "extra ==" in req.replace("extra==", "extra =="):
            continue
        match = _REQ_NAME.match(req)
        if match:
            names.append(canonical(match.group(1)))
    return names


def ssl_context() -> ssl.SSLContext:
    """TLS context on certifi's CA bundle (python.org macOS builds ship none)."""
    try:
        import certifi  # noqa: PLC0415 - optional, runtime dep of kenboard
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def get_json(url: str) -> object:
    """GET ``url`` and decode its JSON body."""
    req = urllib.request.Request(url, headers={"User-Agent": "kenboard-quality-gate"})
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl_context()) as resp:
        return json.load(resp)


def _pypi(name: str) -> dict[str, object]:
    """Fetch the PyPI JSON ``info`` block of a project (latest release)."""
    data = get_json(PYPI_JSON.format(name=name))
    assert isinstance(data, dict)
    info: dict[str, object] = data["info"]
    return info


def _installed(name: str) -> tuple[str, list[str]] | None:
    """Version and requirements of a distribution installed in this venv."""
    try:
        dist = metadata.distribution(name)
    except metadata.PackageNotFoundError:
        return None
    return dist.version, dist.requires or []


def extras_packages() -> list[str]:
    """Names of every package listed in ``[project.optional-dependencies]``."""
    project = tomllib.loads(PYPROJECT.read_text())["project"]
    names = []
    for reqs in project.get("optional-dependencies", {}).values():
        for req in reqs:
            match = _REQ_NAME.match(req)
            if match:
                names.append(canonical(match.group(1)))
    return names


def add_extras(pins: dict[str, str]) -> dict[str, str]:
    """Add the extras and their unconditional requirements, recursively."""
    closure = dict(pins)
    todo = [name for name in extras_packages() if name not in closure]
    while todo:
        name = todo.pop()
        if name in closure:
            continue
        local = _installed(name)
        if local:
            version, requires = local
        else:
            info = _pypi(name)
            version = str(info["version"])
            requires = list(info.get("requires_dist") or [])  # type: ignore[call-overload]
        closure[name] = version
        todo.extend(r for r in unconditional_requirements(requires) if r not in closure)
    return closure


def runtime_closure() -> dict[str, str]:
    """Return ``{canonical name: version}`` for every package prod installs."""
    proc = subprocess.run(
        ["pdm", "export", "--prod", "--without-hashes"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    pins = parse_pins(proc.stdout)
    pins.pop("kenboard", None)
    return dict(sorted(add_extras(pins).items()))


if __name__ == "__main__":
    for pkg, ver in runtime_closure().items():
        print(f"{pkg}=={ver}")
