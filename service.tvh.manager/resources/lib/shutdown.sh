#! /bin/sh
sleep 2
case "$1" in
	ACPI)
		echo 0 > /sys/class/rtc/rtc0/wakealarm
		echo $2 > /sys/class/rtc/rtc0/wakealarm
	;;
	NVRAM)
		nvram-wakeup -C /etc/nvram-wakeup.conf --directisa -s $2
	;;
esac
case "$3" in
    1)
        shutdown -h now "TVHManager shutdown the system"
    ;;
esac
exit 0
