import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path

dest = Path(sys.argv[1]).resolve()
dest.mkdir(parents=True, exist_ok=True)

TOOLS = [
    ("https://github.com/bluenviron/mediamtx/releases/download/v1.21.3/mediamtx_v1.21.3_windows_amd64.zip",
     "https://github.com/bluenviron/mediamtx/releases/download/v1.21.3/checksums.sha256", "mediamtx"),
    ("https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/latest/ffmpeg-n9.0-latest-win64-lgpl-9.0.zip",
     "https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/latest/checksums.sha256", "ffmpeg"),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


for url, sums_url, folder in TOOLS:
    name = url.rsplit("/", 1)[1]
    zpath = dest / name
    print("descargando", name, flush=True)
    urllib.request.urlretrieve(url, zpath)
    sums = urllib.request.urlopen(sums_url).read().decode()
    expected = next((line.split()[0] for line in sums.splitlines() if line.strip().endswith(name)), None)
    actual = sha256(zpath)
    if expected is None or expected.lower() != actual:
        raise SystemExit(f"checksum NO coincide para {name}: esperado {expected}, obtenido {actual}")
    print("checksum OK", name, flush=True)
    out = dest / folder
    with zipfile.ZipFile(zpath) as zf:
        for m in zf.namelist():
            t = (out / m).resolve()
            if out.resolve() not in t.parents and t != out.resolve():
                raise SystemExit(f"ruta insegura: {m}")
        zf.extractall(out)
    zpath.unlink()
    print("extraido en", out, flush=True)

for exe in dest.rglob("*.exe"):
    if exe.name in ("mediamtx.exe", "ffmpeg.exe", "ffprobe.exe"):
        print("listo:", exe)
