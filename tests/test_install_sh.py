from pathlib import Path

INSTALL_SH = Path(__file__).parent.parent / "install.sh"


def test_install_sh_exists():
    assert INSTALL_SH.exists()


def test_install_sh_has_shebang():
    content = INSTALL_SH.read_text()
    assert content.startswith("#!/")


def test_install_sh_has_set_e():
    content = INSTALL_SH.read_text()
    assert "set -e" in content


def test_install_sh_installs_mergerfs():
    content = INSTALL_SH.read_text()
    assert "mergerfs" in content


def test_install_sh_installs_snapraid():
    content = INSTALL_SH.read_text()
    assert "snapraid" in content


def test_install_sh_installs_mdadm():
    content = INSTALL_SH.read_text()
    assert "mdadm" in content


def test_install_sh_installs_linux_headers_meta_package():
    content = INSTALL_SH.read_text()
    apt_line = next(
        (line for line in content.splitlines() if "apt-get install" in line),
        None,
    )
    assert apt_line is not None, "No apt-get install line found"
    assert "linux-headers-$(dpkg --print-architecture)" in apt_line


def test_install_sh_installs_samba():
    content = INSTALL_SH.read_text()
    assert "samba" in content


def test_install_sh_installs_nfs():
    content = INSTALL_SH.read_text()
    assert "nfs-kernel-server" in content


def test_install_sh_installs_pip_requirements():
    content = INSTALL_SH.read_text()
    assert "requirements.txt" in content


def test_install_sh_installs_python_deps_in_venv():
    content = INSTALL_SH.read_text()
    assert "python3 -m venv /opt/fugginnas/venv" in content
    pip_line = next(
        (line for line in content.splitlines() if "pip install" in line),
        None,
    )
    assert pip_line is not None, "No pip install line found"
    assert "/opt/fugginnas/venv/bin/pip" in pip_line
    assert "requirements.txt" in pip_line


def test_install_sh_writes_systemd_unit():
    content = INSTALL_SH.read_text()
    assert "fugginnas.service" in content


def test_install_sh_enables_service():
    content = INSTALL_SH.read_text()
    assert "systemctl enable" in content
