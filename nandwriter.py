__author__ = 'ox-jodm-xo'

import commands
import subprocess
import shlex
import time
import os

sector_size = 512.0
boot_partition_offset = 2048
boot_partition_size = 32768 * 2
root_partition_offset = boot_partition_offset + boot_partition_size


def check_nand_device_driver():
    """
    Checks if SUNXI Nandflash Driver is enabled
    :return True | False:
    """
    s = commands.getoutput('ls /dev/nand')
    if '/dev/nand' in s:
        return True
    print '[ERRO] check_nand_device_driver - nand device driver apparently not enabled'
    print '[----] Please enable \'SUNXI Nandflash Driver\' through menuconfig like following:'
    print '[----] Device Drivers -> Block devices ->'
    print '[----] <*> SUNXI Nandflash Driver'
    print '[----]     [*] Create old nand device names (nanda-nandz)'
    return False


def check_dependences():
    """
    Checks running linux system for dependences
    :return True | False:
    """
    s = commands.getoutput('mkfs.msdos')
    if 'mkfs.fat' in s:
        pass
    else:
        print '[ERRO] check_dependences - mkfs.msdos is not installed'
        print '[----] if you are using a debian system, please install mkfs.msdos using following command:'
        print '[----] apt-get install dosfstools'
        return False
    s = commands.getoutput('fdisk')
    if 'fdisk [options]' in s:
        pass
    else:
        print '[ERRO] check_dependences - fdisk is not installed'
        print '[----] if you are using a debian system, please install fdisk using following command:'
        print '[----] apt-get install util-linux'
        return False
    return True


def get_nand_sectors():
    """
    Get the number of avaliable sectors on the nand device using fdisk
    :return total_sectors:
    """
    s = commands.getoutput('fdisk -l /dev/nand')
    prefix = ', total '
    sufix = ' sectors'
    start = s.find(prefix) + len(prefix)
    s = s[start:]
    end = s.find(sufix)
    return int(s[:end])


def convert_to_mega_bytes(sectors):
    """
    Converts sectors to megabytes
    :param sectors:
    :return megabytes:
    """
    return (sectors * sector_size) / (1000 * 1000)


def calc_root_partition_size():
    """
    Calculates the root partition size depending on the number of sectors
    :return root_partition_size:
    """
    return get_nand_sectors() - root_partition_offset


def create_nand_partitions(boot_p_offset, boot_p_size, root_p_size):
    """
    Creates boot and root partitions
    :param boot_p_offset: boot partition offset
    :param boot_p_size: boot partition size
    :param root_p_size: root partition size
    :return True | False:
    """
    command = 'nand-part -f a20 /dev/nand ' + str(boot_p_offset) + ' \'boot ' + str(boot_p_size) + '\' \'root ' + \
              str(root_p_size) + '\''

    process = subprocess.Popen(shlex.split(command), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    time.sleep(0.2)
    process.stdin.write("Y\n")
    process.stdin.flush()
    dummy = ''
    while process.poll() is None:
        dummy += process.stdout.readline()
    out = process.stdout.read()
    if 'rereading partition table... returned 0' in out or 'rereading partition table... returned 0' in dummy:
        return True
    return False


def write_nand_booloader():
    """
    Writes bootloader to nand
    :return True | False:
    """
    s = commands.getoutput('dd if=nand.mbr.img of=/dev/nand bs=1M count=1')
    if 'copied' in s:
        return True
    return False


def format_boot_partition():
    """
    Format boot partition to FAT16 filesystem type using mkfs
    :return True | False:
    """
    s = commands.getoutput('mkfs.msdos -F16 /dev/nanda')
    if 'using default' in s:
        return True
    return False


def format_root_partition():
    """
    Format root partition to ext4 filesystem type using mkfs
    :return True | False:
    """
    s = commands.getoutput('mkfs.ext4 /dev/nandb')
    if 'done' in s:
        return True
    return False


def init_transfer():
    """
    Creates and mount some directories to aux transfer kernel and rootfs to nand
    :return True | False:
    """
    os.system('mkdir -p /mnt')
    os.system('mkdir -p /media/boot')
    os.system('mkdir -p /media/rootfs')
    os.system('mount /dev/nanda /media/boot/')
    os.system('mount /dev/nandb /media/rootfs/')
    os.system('mount /dev/mmcblk0p1 /mnt/')
    os.system('rm -r /media/rootfs/*')
    return True


def copy_distro_to_nand():
    """
    Copy kernel, script.bin and rootfs to nand
    :return True | False:
    """
    os.system('tar -xf boot-files.tar -C /media/boot/')
    os.system('cp -rv /mnt/boot/uImage /media/boot/')
    os.system('cp -rv /mnt/boot/script.bin /media/boot/')
    os.system('cp -rv /mnt/* /media/rootfs/')
    return True


def finishing():
    """
    Do some commands to complete the copy of the files safely
    :return True | False:
    """
    os.system('sync')
    os.system('umount /media/boot/')
    os.system('umount /media/rootfs/')
    os.system('umount /mnt/')
    return True


if __name__ == '__main__':
    print 'nand-writer v0.0.2'
    if check_nand_device_driver() and check_dependences():
        nand_sectors = get_nand_sectors()
        nand_rootfs_partition_size = calc_root_partition_size()

        print '[INFO] nand-sectors: ' + str(nand_sectors)
        print '[INFO] nand-total-size: ' + str(convert_to_mega_bytes(nand_sectors)) + ' MB'
        print '[INFO] boot-partition-size: ' + str(convert_to_mega_bytes(boot_partition_size)) + ' MB'
        print '[INFO] root-partition-size: ' + str(convert_to_mega_bytes(nand_rootfs_partition_size)) + ' MB'

        option = raw_input('[WARN] This will erase all nand device!\n[WARN] Do you want to continue?  [y/n]: ')
        invalid_option = False
        if isinstance(option, str) and len(option) == 1:
            option = option.lower()
            if 'y' in option:
                pass
            elif 'n' in option:
                print '[INFO] canceled by user!'
                exit(0)
            else:
                invalid_option = True
        else:
            invalid_option = True

        if invalid_option:
            print '[ERRO] invalid option: ' + str(option)
            print '[----] type \'y\' to yes or \'n\' to no: ' + str(option)
            exit(0)

        print '[EXEC] writing bootloader to nand'
        if write_nand_booloader():
            print '[DONE] bootloader written successfully!'
        else:
            print '[ERRO] on writing bootloader to nand'
            exit(0)

        print '[EXEC] creating nand partitions'
        if create_nand_partitions(boot_partition_offset, boot_partition_size, nand_rootfs_partition_size):
            print '[DONE] partitions successfully created!'
        else:
            print '[ERRO] on creating nand partitions'
            exit(0)

        print '[EXEC] formatting boot partition'
        if format_boot_partition():
            print '[DONE] boot partition successfully formatted!'
        else:
            print '[ERRO] on formatting boot partition'
            exit(0)

        print '[EXEC] formatting root partition'
        if format_root_partition():
            print '[DONE] root partition successfully formatted!'
        else:
            print '[ERRO] on formatting root partition'
            exit(0)

        print '[EXEC] creating directories'
        if init_transfer():
            print '[DONE] root partition successfully formatted!'
        else:
            print '[ERRO] on formatting root partition'
            exit(0)

        print '[EXEC] burning distro to nand'
        if copy_distro_to_nand():
            print '[DONE] distro was successfully burned to nand flash'
        else:
            print '[ERRO] error burning distro to nand'
            exit(0)

        print '[EXEC] finishing burn procedure'
        finishing()
        print '[DONE] 100% complete!!!!!! now poweroff the board and takeout sdcard'
