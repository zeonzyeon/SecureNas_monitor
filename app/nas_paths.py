from pathlib import Path, PurePosixPath, PureWindowsPath


class NasPathConfigError(ValueError):
    pass


def is_windows_drive_path(path_value):
    return bool(PureWindowsPath(str(path_value)).drive.endswith(":"))


def validate_nas_monitor_path(path_value, allow_mapped_drive=False):
    if not path_value:
        return

    if is_windows_drive_path(path_value) and not allow_mapped_drive:
        raise NasPathConfigError(
            "NAS_MONITOR_PATH must use a UNC share path, not a mapped drive such as Z:. "
            "Set NAS_ALLOW_MAPPED_DRIVE=true to allow a mapped NAS drive."
        )


def resolve_nas_root(path_value, allow_mapped_drive=False):
    validate_nas_monitor_path(path_value, allow_mapped_drive=allow_mapped_drive)
    return Path(path_value).resolve()


def _to_posix_portal_path(relative_path):
    parts = tuple(part for part in relative_path.parts if part not in {"\\", "/"})
    portal_path = PurePosixPath(*parts).as_posix() if parts else "."
    return f"NAS:/{portal_path}" if portal_path != "." else "NAS:/"


def _relative_to_root(path_value, root_path):
    try:
        return Path(path_value).resolve().relative_to(root_path)
    except (OSError, ValueError):
        pass

    try:
        return PureWindowsPath(str(path_value)).relative_to(PureWindowsPath(str(root_path)))
    except ValueError:
        return None


def _visible_portal_fallback(path_value):
    path = PureWindowsPath(str(path_value))
    parts = [part for part in path.parts if part not in {path.drive, path.root, path.anchor, "\\", "/"}]
    return _to_posix_portal_path(PurePosixPath(*parts))


def to_portal_path(path_value, root_path):
    if not path_value:
        return None

    if root_path:
        relative_path = _relative_to_root(path_value, root_path)
        if relative_path is not None:
            return _to_posix_portal_path(relative_path)

    return _visible_portal_fallback(path_value)
