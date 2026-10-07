# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""扫描本机所有 VS Code 系 IDE 的身份与目录坐标（只读，不修改任何文件）。

身份四件套一律从各 IDE 自带的 product.json 推导，不靠记忆里的路径：
    dataFolderName  -> %USERPROFILE%\\<dataFolderName>\\extensions   扩展目录与 argv.json
    nameShort       -> %APPDATA%\\<nameShort>\\User                   settings.json / state.vscdb
    applicationName -> <安装目录>\\bin\\<applicationName>.cmd         CLI
    extensionsGallery.serviceUrl -> 该分支用哪个扩展市场

用法：
    uv run scan_ides.py                          # 人类可读表格
    uv run scan_ides.py --json                   # JSON（给脚本/模型读）
    uv run scan_ides.py --has <publisher.name>   # 哪个分支已装这个扩展
    uv run scan_ides.py --root "D:\\Tools"       # 追加安装根目录（可重复）

本文件同时是 port_extension.py 的公共库（盘符扫描、身份解析、注册表读写）。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA") or HOME / "AppData" / "Local")
APPDATA = Path(os.environ.get("APPDATA") or HOME / "AppData" / "Roaming")


# ---------------------------------------------------------------- 安装根目录扫描


def drive_letters() -> list[str]:
    """枚举本机盘符；用 os.listdrives（3.12+）避免逐个盘符 stat 卡在网络盘上。"""
    if hasattr(os, "listdrives"):  # Python 3.12+
        return [d.rstrip("\\/") for d in os.listdrives()]
    return [f"{c}:" for c in "CDEFG" if Path(f"{c}:/").exists()]  # 兜底


def default_roots() -> list[Path]:
    """默认安装根目录：本机 + 其他盘的用户级 Programs（IDE 常被装到非系统盘）。"""
    roots = [LOCALAPPDATA / "Programs", Path("C:/Program Files"), Path("C:/Program Files (x86)")]
    tail = None
    try:  # C:\\Users\\x -> Users\\x，用来在其他盘上找同名用户目录
        tail = Path(*HOME.parts[1:])
    except IndexError:
        pass
    for d in drive_letters():
        roots.append(Path(f"{d}/") / "Program Files")
        roots.append(Path(f"{d}/") / "Program Files (x86)")
        if tail is not None:
            roots.append(Path(f"{d}/") / tail / "AppData" / "Local" / "Programs")
    seen, out = set(), []
    for r in roots:
        key = str(r).lower()
        if key not in seen and r.is_dir():
            seen.add(key)
            out.append(r)
    return out


def find_products(roots: list[Path]) -> list[Path]:
    """找 <安装根>/resources/app/product.json；浅层没找到再下探一层（升级残留/版本化目录）。"""
    shallow: list[Path] = []
    deep: list[Path] = []
    for root in roots:
        for entry in sorted(root.iterdir()) if root.is_dir() else []:
            direct = entry / "resources" / "app" / "product.json"
            if direct.is_file():
                shallow.append(direct)
                continue
            if not entry.is_dir():
                continue
            try:
                subs = list(entry.iterdir())
            except OSError:
                continue
            for sub in subs:
                nested = sub / "resources" / "app" / "product.json"
                if nested.is_file():
                    deep.append(nested)
    return shallow + deep


def data_dir_ides() -> dict[str, Path]:
    """~/.<x>/argv.json 是 VS Code 系分支的数据目录特征（装没装都能认出来）。"""
    out = {}
    for p in HOME.glob(".*"):
        if p.is_dir() and (p / "argv.json").is_file():
            out[p.name.lstrip(".")] = p
    return out


def read_product(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return None


def guess_user_data(data_folder_name: str) -> Path | None:
    """product.json 缺失时，按名字在 %APPDATA% 里认领运行数据目录（.trae-cn -> Trae CN）。"""
    base = data_folder_name.lstrip(".")
    wanted = {base.lower(), base.replace("-", " ").lower(), base.replace("-", "").lower()}
    wanted = {w.replace(" ", "") for w in wanted}
    if APPDATA.is_dir():
        for p in APPDATA.iterdir():
            if p.is_dir() and p.name.lower().replace(" ", "") in wanted:
                return p
    return None


# ------------------------------------------------------------------ 身份解析


def scan(extra_roots: list[str] | None = None) -> list[dict]:
    """返回本机所有 VS Code 系分支的坐标（已装/未装都列）。"""
    extra_roots = extra_roots or []
    data_dirs = data_dir_ides()
    rows: dict[str, dict] = {}

    for pj in find_products(default_roots() + [Path(r) for r in extra_roots]):
        d = read_product(pj)
        if not d or not d.get("dataFolderName"):
            continue
        rows.setdefault(d["dataFolderName"], {}).update(
            dataFolderName=d["dataFolderName"],
            nameShort=d.get("nameShort", ""),
            nameLong=d.get("nameLong", ""),
            applicationName=d.get("applicationName", ""),
            version=d.get("version", ""),
            installDir=str(pj.parents[2]),
            productJson=str(pj),
            gallery=(d.get("extensionsGallery") or {}).get("serviceUrl", ""),
        )

    # 数据目录兜底：product.json 没找到（正在升级、装到非常规位置）也要能推出扩展目录
    for name in data_dirs:
        key = f".{name}"
        if key in rows:
            continue
        guessed = guess_user_data(key)
        rows[key] = {
            "dataFolderName": key,
            "nameShort": guessed.name if guessed else name,
            "dataDirOnly": True,
        }

    result = []
    for key, row in rows.items():
        df = row.get("dataFolderName") or key
        ext_dir = HOME / df / "extensions"
        user_data = APPDATA / (row.get("nameShort") or df.lstrip("."))
        if not user_data.is_dir() and row.get("dataDirOnly"):
            guessed = guess_user_data(df)
            if guessed:
                user_data = guessed
                row["nameShort"] = guessed.name
        row.update(
            extensionsDir=str(ext_dir),
            extensionsDirExists=ext_dir.is_dir(),
            userDataDir=str(user_data),
            userDataDirExists=user_data.is_dir(),
            argvJson=str(HOME / df / "argv.json"),
            cli=find_cli(row),
        )
        result.append(row)

    result.sort(key=lambda r: (not r.get("extensionsDirExists"), r.get("nameShort") or r["dataFolderName"]))
    return result


def find_cli(row: dict) -> str | None:
    """定位该分支的 CLI（bin/<applicationName>[.cmd]）；找不到返回 None。"""
    if not row.get("installDir"):
        return None
    for name in (f"{row.get('applicationName')}.cmd", row.get("applicationName") or ""):
        if not name:
            continue
        cand = Path(row["installDir"]) / "bin" / name
        if cand.is_file():
            return str(cand)
    return None


def _norm(s: str) -> str:
    return s.strip().lower().replace(" ", "").replace("-", "").replace("_", "")


def resolve(key: str, extra_roots: list[str] | None = None) -> dict:
    """按 dataFolderName / nameShort / 安装目录路径解析出一个分支；歧义时抛错列出候选。"""
    rows = scan(extra_roots)
    if os.path.isdir(key):  # 直接给路径
        p = Path(key).resolve()
        for r in rows:
            if r.get("installDir") and Path(r["installDir"]).resolve() == p:
                return r
    k = _norm(key)
    hits = [
        r
        for r in rows
        if _norm(r["dataFolderName"].lstrip(".")) == k
        or _norm(r.get("nameShort") or "") == k
        or _norm(Path(r.get("installDir") or "").name) == k
    ]
    if len(hits) == 1:
        return hits[0]
    names = ", ".join(sorted({r.get("nameShort") or r["dataFolderName"] for r in rows}))
    if not hits:
        raise SystemExit(f"没找到分支 {key!r}；本机可选：{names}")
    raise SystemExit(f"{key!r} 命中多个分支，请用 --json 里的 dataFolderName 精确指定：{names}")


# ------------------------------------------------------------------ 扩展目录与注册表


def find_in_dir(ext_dir: Path, ext_id: str) -> list[str]:
    """按 publisher.name 找扩展目录（兼容 <id>-<ver> 与 <id>-<ver>-<platform> 两种命名）。"""
    if not ext_dir.is_dir():
        return []
    low = ext_id.lower()
    return sorted(p.name for p in ext_dir.iterdir() if p.is_dir() and p.name.lower().startswith(low + "-"))


def registry_path(row: dict, profile: str | None = None) -> Path:
    """扩展注册表路径。默认 profile 用扩展目录根的 extensions.json；
    具名 profile 的注册表在 <userData>/User/profiles/<profile>/extensions.json。"""
    if profile and profile != "__default__profile__":
        return Path(row["userDataDir"]) / "User" / "profiles" / profile / "extensions.json"
    return Path(row["extensionsDir"]) / "extensions.json"


def list_profiles(row: dict) -> list[str]:
    d = Path(row["userDataDir"]) / "User" / "profiles"
    return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.is_dir() else []


def load_registry(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    txt = path.read_text(encoding="utf-8-sig").strip()
    if not txt:
        return []
    try:
        data = json.loads(txt)
    except json.JSONDecodeError as e:
        raise SystemExit(f"{path} 不是合法 JSON（{e}）；先手工修好再跑，别硬写") from e
    return data if isinstance(data, list) else []


def save_registry(path: Path, entries: list[dict]) -> None:
    """写回注册表；首次改动留 .bak（用户既有习惯，回滚用）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and not path.with_suffix(path.suffix + ".bak").exists():
        path.with_suffix(path.suffix + ".bak").write_bytes(path.read_bytes())
    path.write_text(json.dumps(entries, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="")


def registry_entry(ext_id: str, version: str, abs_dir: Path, uuid: str | None = None) -> dict:
    """构造一条注册条目。$mid/path/scheme 三键是 VS Code 系 IDE 自己写的最小 URI 形式。"""
    ident: dict = {"id": ext_id}
    if uuid:
        ident["uuid"] = uuid
    # VS Code 的 URI.path 形如 /c:/Users/...（盘符小写、其余大小写原样）
    p = abs_dir.as_posix()
    if len(p) > 1 and p[1] == ":":
        p = p[0].lower() + p[1:]
    return {
        "identifier": ident,
        "version": version,
        "location": {"$mid": 1, "path": "/" + p.lstrip("/"), "scheme": "file"},
        "relativeLocation": abs_dir.name,
        "metadata": {
            "isApplicationScoped": False,
            "installedTimestamp": int(time.time() * 1000),
            "source": "vsix",
            "targetPlatform": "undefined",
            "updated": False,
            "private": False,
            "isPreReleaseVersion": False,
            "hasPreReleaseVersion": False,
        },
    }


def read_manifest(ext_dir: Path) -> dict:
    p = ext_dir / "package.json"
    if not p.is_file():
        raise SystemExit(f"{ext_dir} 里没有 package.json，不像一个扩展目录")
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{p} 不是合法 JSON：{e}") from e


def is_running(row: dict) -> bool:
    """粗判目标 IDE 是否在跑（Windows 用 tasklist 匹配 <nameShort>.exe）。"""
    if os.name != "nt":
        return False
    exe = f"{row.get('nameShort') or ''}.exe"
    if len(exe) <= 4:
        return False
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe}", "/NH"],
            capture_output=True,
            text=True,
            timeout=20,
            encoding="utf-8",
            errors="replace",
        ).stdout
    except Exception:  # noqa: BLE001
        return False
    return exe.lower() in out.lower()


def cli_list_extensions(row: dict) -> list[str] | None:
    """用目标分支自带 CLI 列已装扩展（拿不到 CLI 返回 None）。"""
    cli = row.get("cli") or find_cli(row)
    if not cli:
        return None
    try:
        out = subprocess.run(
            [cli, "--list-extensions", "--show-versions"],
            capture_output=True,
            text=True,
            timeout=180,
            encoding="utf-8",
            errors="replace",
        ).stdout
    except Exception:  # noqa: BLE001
        return None
    return [ln.strip() for ln in out.splitlines() if "@" in ln]


# ------------------------------------------------------------------ CLI


def print_rows(rows: list[dict]) -> None:
    for r in rows:
        title = r.get("nameShort") or r["dataFolderName"]
        if r.get("version"):
            title += f"  v{r['version']}"
        print(f"● {title}")
        print(f"  数据目录 dataFolderName = {r['dataFolderName']}")
        print(f"  扩展目录 {r['extensionsDir']}{'' if r.get('extensionsDirExists') else '  (不存在)'}")
        if r.get("hasExtension") is not None:
            print(f"  命中扩展 {r['hasExtension'] or '无'}")
        print(f"  运行数据 {r['userDataDir']}{'' if r.get('userDataDirExists') else '  (不存在)'}")
        if r.get("gallery"):
            print(f"  市场     {r['gallery']}")
        if r.get("installDir"):
            print(f"  安装目录 {r['installDir']}")
        if r.get("cli"):
            print(f"  CLI      {r['cli']}")
        if r.get("dataDirOnly"):
            print("  注：未找到安装目录（product.json），仅按数据目录推断；扩展目录仍有效")
        print()


def main() -> int:
    ap = argparse.ArgumentParser(description="扫描本机 VS Code 系 IDE 的身份与目录（只读）")
    ap.add_argument("--root", action="append", default=[], help="追加安装根目录，可重复")
    ap.add_argument("--has", metavar="ID", help="检查哪个分支装了该扩展（publisher.name）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    rows = scan(args.root)
    if args.has:
        for r in rows:
            r["hasExtension"] = find_in_dir(Path(r["extensionsDir"]), args.has)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("没找到任何 VS Code 系 IDE；用 --root 指定安装根目录再试")
        return 1
    print_rows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
