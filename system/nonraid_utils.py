def generate_mdadm_create(devices: list, level: int, name: str = 'md0') -> str:
    count = len(devices)
    device_list = ' '.join(devices)
    return f"mdadm --create /dev/{name} --level={level} --raid-devices={count} {device_list}"


def generate_fstab_line(device: str, mountpoint: str, fstype: str = 'ext4') -> str:
    return f"{device}  {mountpoint}  {fstype}  defaults  0  2"
