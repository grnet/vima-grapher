# vima-grapher

Α WSGI python script that serves KVM RRD graphs for use with [Ganetimgr](https://github.com/grnet/ganetimgr).

This repository consists of thee things:
 * A collectd plugin that gets CPU and net stats from KVM processes (unfortunately no support for Xen VMs)
 * A sample collectd daemon conf to receive and store the graphs
 * A python WSGI script that serves the requests that ganetimgr makes and displays the rrd on it's UI
   * along with sample gunicorn and nginx config to server the script
