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
    assert "linux-headers-amd64" in content


def test_install_sh_installs_samba():
    content = INSTALL_SH.read_text()
    assert "samba" in content


def test_install_sh_installs_nfs():
    content = INSTALL_SH.read_text()
    assert "nfs-kernel-server" in content


def test_install_sh_installs_pip_requirements():
    content = INSTALL_SH.read_text()
    assert "requirements.txt" in content


def test_install_sh_allows_debian_pep668_pip_install():
    content = INSTALL_SH.read_text()
    assert "--break-system-packages" in content


def test_install_sh_writes_systemd_unit():
    content = INSTALL_SH.read_text()
    assert "fugginnas.service" in content


def test_install_sh_enables_service():
    content = INSTALL_SH.read_text()
    assert "systemctl enable" in content
