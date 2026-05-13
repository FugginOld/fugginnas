def generate_smb_block(name: str, path: str, guest_ok: bool,
                       username: str = "", password: str = "") -> str:
    lines = [f"[{name}]", f"   path = {path}", "   browseable = yes", "   writable = yes"]
    if guest_ok:
        lines.append("   guest ok = yes")
    else:
        lines += ["   guest ok = no", f"   valid users = {username}"]
    return "\n".join(lines) + "\n"
