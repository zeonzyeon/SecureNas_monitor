from pathlib import Path, PurePosixPath, PureWindowsPath


class NasPathConfigError(ValueError):
    pass


# Windows 매핑 드라이브 판별
def is_windows_drive_path(path_value):
    return bool(PureWindowsPath(str(path_value)).drive.endswith(":"))


# NAS 경로 설정 검증
def validate_nas_monitor_path(path_value, allow_mapped_drive=False):
    if not path_value:
        return

    if is_windows_drive_path(path_value) and not allow_mapped_drive:
        raise NasPathConfigError(
            "NAS_MONITOR_PATH must use a UNC share path, not a mapped drive such as Z:. "
            "Remove the user's Z: drive mapping and let only the web server account access the NAS share."
        )


# NAS 루트 경로 해석
def resolve_nas_root(path_value, allow_mapped_drive=False):
    validate_nas_monitor_path(path_value, allow_mapped_drive=allow_mapped_drive)
    return Path(path_value).resolve()


# 대시보드 표시용 NAS 경로 변환
def to_portal_path(path_value, root_path):
    if not path_value:
        return None

    try:
        relative_path = Path(path_value).resolve().relative_to(root_path)
    except (OSError, ValueError):
        return "NAS:/hidden"

    portal_path = PurePosixPath(*relative_path.parts).as_posix()
    return f"NAS:/{portal_path}" if portal_path != "." else "NAS:/"
