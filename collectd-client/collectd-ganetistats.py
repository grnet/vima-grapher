#!/usr/bin/env python

import os
import collectd

from hashlib import md5 

from glob import glob

cpu_q = {}
stats_frequency = 10
def read_int(file):
    f = open(file, "r")
    try:
        val = int(f.read())
    except ValueError:
        val = None
    finally:
        f.close()
    return val 


def anonymize_hostname(hostname):
    #return md5(hostname).hexdigest()
    return hostname


def get_vcpus(pid):
    """Get a KVM instance vCPU count by looking at its fd's"""
    vcpus = 0 
    for fd in glob("/proc/%d/fd/*" % pid):
        # XXX: sad but trueeeeeeeeeeee
        try:
            myfd = os.readlink(fd)
        except OSError:
            continue
        if myfd == "anon_inode:kvm-vcpu":
            vcpus += 1
    return vcpus


def netstats(data=None):
    for dir in glob("/var/run/ganeti/kvm-hypervisor/nic/*"):
        if not os.path.isdir(dir):
            continue
        hostname = os.path.basename(dir)
        for nic in glob(os.path.join(dir, "*")):
            idx = int(os.path.basename(nic))
            with open(nic) as nicfile:
                try:
                    iface = nicfile.readline().strip()
                except EnvironmentError:
                    continue
            if not os.path.isdir("/sys/class/net/%s" % iface):
                continue
            bytes_in = read_int("/sys/class/net/%s/statistics/rx_bytes" % iface)
            bytes_out = read_int("/sys/class/net/%s/statistics/tx_bytes" % iface)
            vl = collectd.Values(type="counter")
            vl.host = anonymize_hostname(hostname)
            vl.plugin = "interface"
            vl.type = "if_octets"
            vl.type_instance = "eth%d" % idx
            vl.dispatch(values=[bytes_out, bytes_in])


def cpustats(data=None):
    for file in glob("/var/run/ganeti/kvm-hypervisor/pid/*"):
        instance = os.path.basename(file)
        try:
            pid = int(open(file, "r").read())
            proc = open("/proc/%d/stat" % pid, "r")
            cputime = [int(proc.readline().split()[42])]
        except EnvironmentError:
            continue
        vcpus = get_vcpus(pid)
        proc.close()
        # If vcpus = 0 then we probably got wrong pid
        if (vcpus > 0):
            vl = collectd.Values(type="counter")
            vl.host = anonymize_hostname(instance)
            vl.plugin = "cpu"
            vl.type = "virt_cpu_total"
            total = sum(cputime) * 100 / (vcpus * os.sysconf("SC_CLK_TCK"))
            global cpu_q
            if vl.host not in cpu_q.keys():
                cpu_q[vl.host] = total
            else:
                diff = abs(cpu_q[vl.host] - total)
                cpu_q[vl.host] = total
                if diff < stats_frequency*110:
                    vl.dispatch(values=[total])

collectd.register_read(cpustats,stats_frequency,None,'cpustats')
collectd.register_read(netstats,stats_frequency,None,'netstats')

# vim: set ts=4 sts=4 et sw=4 :
