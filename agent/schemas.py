"""هياكل البيانات المشتركة بين مراحل التخطيط والكتابة والتشغيل."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class FileSpec:
    path: str
    purpose: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileSpec":
        if not isinstance(data, dict):
            raise ValueError("كل عنصر في files يجب أن يكون كائناً JSON.")
        path = data.get("path")
        purpose = data.get("purpose")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("كل ملف في الخطة يحتاج path صالحاً.")
        if not isinstance(purpose, str) or not purpose.strip():
            raise ValueError(f"الملف {path} يحتاج purpose واضحاً.")
        return cls(path=path.strip(), purpose=purpose.strip())


@dataclass(frozen=True)
class Plan:
    project_name: str
    language: str
    description: str
    files: list[FileSpec]
    dependencies: list[str]
    test_command: str
    run_command: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Plan":
        if not isinstance(data, dict):
            raise ValueError("الخطة يجب أن تكون كائن JSON.")
        required = ("project_name", "language", "description", "files", "dependencies", "test_command", "run_command")
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f"الخطة ناقصة الحقول: {', '.join(missing)}")

        project_name = data["project_name"]
        language = data["language"]
        description = data["description"]
        test_command = data["test_command"]
        run_command = data["run_command"]
        raw_files = data["files"]
        dependencies = data["dependencies"]

        if not isinstance(project_name, str) or not project_name.strip():
            raise ValueError("project_name غير صالح.")
        if not isinstance(language, str) or language.lower().strip() != "python":
            raise ValueError("اللغة المدعومة حالياً هي Python فقط.")
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description مطلوب في الخطة.")
        if not isinstance(raw_files, list) or not raw_files:
            raise ValueError("الخطة يجب أن تحتوي ملفات.")
        files = [FileSpec.from_dict(item) for item in raw_files]
        if not any("test" in item.path.lower() for item in files):
            raise ValueError("الخطة يجب أن تتضمن ملف اختبار واحداً على الأقل.")
        if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
            raise ValueError("dependencies يجب أن تكون قائمة نصوص.")
        if not isinstance(test_command, str) or not test_command.strip():
            raise ValueError("test_command مطلوب.")
        if not isinstance(run_command, str):
            raise ValueError("run_command يجب أن يكون نصاً.")

        return cls(
            project_name=project_name.strip(),
            language="python",
            description=description.strip(),
            files=files,
            dependencies=[item.strip() for item in dependencies if item.strip()],
            test_command=test_command.strip(),
            run_command=run_command.strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FileContent:
    path: str
    content: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileContent":
        if not isinstance(data, dict):
            raise ValueError("بيانات الملف يجب أن تكون كائن JSON.")
        path = data.get("path")
        content = data.get("content")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("ملف مولّد بدون path صالح.")
        if not isinstance(content, str):
            raise ValueError(f"محتوى الملف {path} يجب أن يكون نصاً.")
        return cls(path=path.strip(), content=content)


@dataclass(frozen=True)
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    timed_out: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
