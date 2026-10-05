"""إدارة ملفات المشاريع المولدة مع منع الخروج من workspace."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from .schemas import FileContent

WORKSPACE_ROOT = Path("workspace")
MAX_FILE_BYTES = 200 * 1024
MAX_FILES = 50


def project_directory(project_name: str) -> Path:
    root = WORKSPACE_ROOT.resolve()
    target = (root / project_name).resolve()
    if target.parent != root:
        raise ValueError("اسم المشروع يحاول الخروج من مجلد workspace.")
    return target


def safe_path(project_dir: Path, relative_path: str) -> Path:
    pure = PurePosixPath(relative_path)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"مسار غير آمن ومرفوض: {relative_path}")
    if not relative_path.strip() or relative_path.endswith("/"):
        raise ValueError(f"مسار ملف غير صالح: {relative_path}")

    root = project_dir.resolve()
    target = (root / Path(*pure.parts)).resolve()
    if target == root or root not in target.parents:
        raise ValueError(f"المسار يخرج من مجلد المشروع: {relative_path}")
    return target


def write_files(project_name: str, files: list[FileContent]) -> Path:
    if len(files) > MAX_FILES:
        raise ValueError(f"الحد الأقصى هو {MAX_FILES} ملفاً لكل مشروع.")

    project_dir = project_directory(project_name)
    project_dir.mkdir(parents=True, exist_ok=True)

    existing = [
        path for path in project_dir.rglob("*")
        if path.is_file() and ".agent_deps" not in path.relative_to(project_dir).parts
    ]
    existing_relative = {str(path.relative_to(project_dir)) for path in existing}
    incoming = {item.path for item in files}
    if len(existing_relative | incoming) > MAX_FILES:
        raise ValueError(f"الحد الأقصى هو {MAX_FILES} ملفاً لكل مشروع.")

    for item in files:
        encoded = item.content.encode("utf-8")
        if len(encoded) > MAX_FILE_BYTES:
            raise ValueError(f"الملف {item.path} يتجاوز حد 200KB.")
        target = safe_path(project_dir, item.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(encoded)

    return project_dir


def read_project_files(project_dir: Path) -> list[FileContent]:
    files: list[FileContent] = []
    for path in sorted(project_dir.rglob("*")):
        relative = path.relative_to(project_dir)
        if (
            not path.is_file()
            or path.name == "agent_report.json"
            or ".agent_deps" in relative.parts
        ):
            continue
        files.append(FileContent(path=str(relative), content=path.read_text(encoding="utf-8")))
    return files
