def generate_export_line(path: str, allowed_hosts: str, readonly: bool) -> str:
    options = "ro" if readonly else "rw"
    return f"{path} {allowed_hosts}({options},sync,no_subtree_check)\n"
