_VALID_POLICIES = {"mfs", "lfs", "existing"}


def build_mount_string(sources: list[str], target: str, write_policy: str) -> str:
    source_str = ":".join(sources)
    return (
        f"{source_str} {target} fuse.mergerfs "
        f"defaults,allow_other,use_ino,category.create={write_policy},"
        f"moveonenospc=1,dropcacheonclose=1,minfreespace=200M 0 0"
    )
