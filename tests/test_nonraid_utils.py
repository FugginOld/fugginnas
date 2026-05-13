from system.nonraid_utils import generate_mdadm_create, generate_fstab_line


def test_generate_mdadm_create_basic():
    cmd = generate_mdadm_create(['/dev/sdb', '/dev/sdc'], level=1)
    assert '--create' in cmd
    assert '/dev/md0' in cmd
    assert '--level=1' in cmd
    assert '/dev/sdb' in cmd
    assert '/dev/sdc' in cmd


def test_generate_mdadm_create_raid_device_count():
    cmd = generate_mdadm_create(['/dev/sdb', '/dev/sdc', '/dev/sdd'], level=5)
    assert '--raid-devices=3' in cmd


def test_generate_mdadm_create_custom_name():
    cmd = generate_mdadm_create(['/dev/sdb', '/dev/sdc'], level=0, name='md1')
    assert '/dev/md1' in cmd


def test_generate_mdadm_create_includes_all_devices():
    devices = ['/dev/sdb', '/dev/sdc', '/dev/sdd', '/dev/sde']
    cmd = generate_mdadm_create(devices, level=6)
    for d in devices:
        assert d in cmd


def test_generate_mdadm_create_level_6():
    cmd = generate_mdadm_create(['/dev/sdb', '/dev/sdc'], level=6)
    assert '--level=6' in cmd


def test_generate_mdadm_create_level_10():
    cmd = generate_mdadm_create(['/dev/sdb', '/dev/sdc', '/dev/sdd', '/dev/sde'], level=10)
    assert '--level=10' in cmd
    assert '--raid-devices=4' in cmd


def test_generate_fstab_line_basic():
    line = generate_fstab_line('/dev/md0', '/mnt/raid')
    assert '/dev/md0' in line
    assert '/mnt/raid' in line
    assert 'ext4' in line


def test_generate_fstab_line_custom_fstype():
    line = generate_fstab_line('/dev/md0', '/mnt/raid', fstype='xfs')
    assert 'xfs' in line


def test_generate_fstab_line_has_options():
    line = generate_fstab_line('/dev/md0', '/mnt/raid')
    parts = line.split()
    assert len(parts) >= 4
