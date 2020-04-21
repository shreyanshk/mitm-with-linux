import subprocess
import queue
import threading
import signal
import time
import os


d_p = dict()
d_t = dict()
q_out = queue.Queue()

DEBUG = 0
ONTERM = os.environ.get("ONTERM", None)


def cmd(cmd, iden=None, wait=True):
    if wait:
        time.sleep(0.01)
    if DEBUG:
        print(cmd)
    p = subprocess.Popen(
            cmd.split(" "),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            )
    p.wait() if wait else d_p.update({iden: p})
    for line in p.stdout:
        if line in [None, "", " ", "\n", " \n"]:
            continue
        q_out.put(line) if wait else q_out.put(f"{iden}: {line}")


def output():
    while True:
        line = q_out.get(block=True, timeout=None)
        if line is None:
            break
        print(line, end="")


def handle_sigs(signal, frame):
    for _, p in d_p.items():
        p.terminate()
    time.sleep(1)
    cmd("iw dev wlp2s0 del")
    cmd("iw dev wlp2s1 del")
    cmd("iptables -F")
    cmd("iw phy phy0 interface add wlp2s0 type managed addr <redacted>")
    with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
        f.write("0")
    with open("/proc/sys/net/ipv4/conf/all/arp_filter", "w") as f:
        f.write("0")
    if ONTERM:
        for i in range(1, 8):
            with open(f"/sys/devices/system/cpu/cpu{i}/online", "w") as f:
                f.write("1")
        with open("/sys/devices/system/cpu/intel_pstate/no_turbo", "w") as f:
            f.write("0")
        cmd(
            "systemctl start"
            " systemd-logind.service"
            " display-manager.service"
        )
    cmd(
        "systemctl start"
        " network-manager.service"
        " firewall.service"
        " wpa_supplicant.service"
    )
    with open("/etc/resolv.conf", "w") as f:
        f.write("")
    q_out.put(None)


signal.signal(signal.SIGINT, handle_sigs)
cmd(
    "systemctl stop"
    " network-manager.service"
    " wpa_supplicant.service"
    " firewall.service"
)
if ONTERM:
    print("ONTERM detected!")
    cmd(
        "systemctl stop"
        " display-manager.service"
        " systemd-logind.service"
    )
    for i in range(1, 8):
        with open(f"/sys/devices/system/cpu/cpu{i}/online", "w") as f:
            f.write("0")
    with open("/sys/devices/system/cpu/intel_pstate/no_turbo", "w") as f:
        f.write("1")
cmd("iptables -F")
with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
    f.write("1")
with open("/proc/sys/net/ipv4/conf/all/arp_filter", "w") as f:
    f.write("1")
d_t['io'] = threading.Thread(target=output)
d_t['io'].start()
cmd("iw dev wlp2s0 del")
cmd("iw phy phy0 interface add wlp2s0 type managed addr <redacted>")
cmd("iw phy phy0 interface add wlp2s1 type managed addr <redacted>")
d_t['wpa'] = threading.Thread(
        target=cmd,
        args=(
            "wpa_supplicant -Dnl80211 -iwlp2s0 -cwpacfg",
            "wpa", False,
            )
        )
d_t['wpa'].start()
d_t['ap'] = threading.Thread(
        target=cmd,
        args=("hostapd hostapdconf", "ap", False),
        )
d_t['ap'].start()
d_t['dhcp'] = threading.Thread(
        target=cmd,
        args=("dnsmasq -C ./dnsmasq.conf", "dhcp", False)
        )
d_t['dhcp'].start()
cmd("ip addr add 172.16.48.1/22 dev wlp2s1")
cmd("ip addr add 172.16.48.148/22 dev wlp2s0")
cmd("ip route add default via 172.16.48.1 dev wlp2s0")
cmd("iptables -A FORWARD --in-interface wlp2s1 -j ACCEPT")
cmd("iptables --table nat -A POSTROUTING --out-interface wlp2s0 -j MASQUERADE")
cmd(
    "iptables -I PREROUTING 1 -t nat -m tcp -p tcp --dport 443"
    " -d 172.16.0.154 -j DNAT --to-destination 172.16.48.148:8080"
)
d_t['proxy'] = threading.Thread(
        target=cmd,
        args=("./proxy", "proxy", False)
        )
d_t['proxy'].start()

with open("/etc/resolv.conf", "w") as f:
    f.write("nameserver 172.16.1.11")

for _, val in d_t.items():
    val.join()
