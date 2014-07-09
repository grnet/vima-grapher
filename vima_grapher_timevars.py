
#!/usr/bin/env python

import gd
import os
import sys
import subprocess

from cgi import escape
from cStringIO import StringIO
#from flup.server.fcgi import WSGIServer

import rrdtool

IMAGE_WIDTH = 210
WIDTH = 68
HEIGHT = 10

RRD_PREFIX = "/var/lib/collectd/rrd/"
GRAPH_PREFIX = "/var/cache/vima/"
FONT = "/usr/share/fonts/truetype/ttf-dejavu/DejaVuSansMono.ttf"
FONT = "/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans.ttf"

BAR_BORDER_COLOR = (0x5c, 0xa1, 0xc0)
BAR_BG_COLOR = (0xea, 0xea, 0xea)


class InternalError(Exception):
    pass


class NotFound(Exception):
    pass


def read_file(filepath):
    try:
        f = open(filepath, "r")
    except EnvironmentError, e:
        raise InternalError(str(e))

    try:
        data = f.read()
    except EnvironmentError, e:
        raise InternalError(str(e))
    finally:
        f.close()

    return data


def draw_cpu_bar(hostname):
    fname = os.path.join(RRD_PREFIX, os.path.basename(hostname), "cpu", "virt_cpu_total.rrd")

    try:
        values = rrdtool.fetch(fname, "AVERAGE")[2][-20:]
    except rrdtool.error, e:
        #raise InternalError(str(e))
        values = [(0.0, )]

    v = [x[0] for x in values if x[0] is not None]
    if not v:
        # Fallback in case we only get NaNs
        v = [0.0]
    # Pick the last value
    value = v[-1]

    image = gd.image((IMAGE_WIDTH, HEIGHT))

    border_color = image.colorAllocate(BAR_BORDER_COLOR)
    white = image.colorAllocate((0xff, 0xff, 0xff))
    background_color = image.colorAllocate(BAR_BG_COLOR)

    if value >= 90.0:
        line_color = image.colorAllocate((0xff, 0x00, 0x00))
    elif value >= 75.0:
        line_color = image.colorAllocate((0xda, 0xaa, 0x00))
    else:
        line_color = image.colorAllocate((0x00, 0xa1, 0x00))

    image.rectangle((0,0), (WIDTH-1, HEIGHT-1), border_color, background_color)
    image.rectangle((1,1), (int(value/100.0 * (WIDTH - 2)), HEIGHT - 2), line_color, line_color)
    image.string_ttf(FONT, 8.0, 0.0, (WIDTH + 1, HEIGHT - 1), "CPU: %.1f%%" % value, white)

    io = StringIO()
    image.writePng(io)
    io.seek(0)
    data = io.getvalue()
    io.close()
    return data

#def draw_net_bar(hostname, iface='eth0'):
#    fname = os.path.join(RRD_PREFIX, os.path.basename(hostname),
#                         "interface", "if_octets-" + iface + ".rrd")

def draw_net_bar(hostname):
    fname = os.path.join(RRD_PREFIX, os.path.basename(hostname),
                         "interface", "if_octets-eth0.rrd")

    try:
        values = rrdtool.fetch(fname, "AVERAGE")[2][-20:]
    except rrdtool.error, e:
        #raise InternalError(str(e))
        values = [(0.0, 0.0)]

    v = [x for x in values if x[0] is not None and x[1] is not None]
    if not v:
        # Fallback in case we only get NaNs
        v = [(0.0, 0.0)]

    rx_value, tx_value = v[-1]

    # Convert to bits
    rx_value = rx_value * 8 / 10**6
    tx_value = tx_value * 8 / 10**6

    max_value = (int(max(rx_value, tx_value)/50) + 1) * 50.0

    image = gd.image((IMAGE_WIDTH, HEIGHT))

    border_color = image.colorAllocate(BAR_BORDER_COLOR)
    white = image.colorAllocate((0xff, 0xff, 0xff))
    background_color = image.colorAllocate(BAR_BG_COLOR)

    tx_line_color = image.colorAllocate((0x00, 0xa1, 0x00))
    rx_line_color = image.colorAllocate((0x00, 0x00, 0xa1))

    image.rectangle((0,0), (WIDTH-1, HEIGHT-1), border_color, background_color)
    image.rectangle((1,1), (int(tx_value/max_value * (WIDTH-2)), HEIGHT/2 - 1), tx_line_color, tx_line_color)
    image.rectangle((1,HEIGHT/2), (int(rx_value/max_value * (WIDTH-2)), HEIGHT - 2), rx_line_color, rx_line_color)
    image.string_ttf(FONT, 8.0, 0.0, (WIDTH + 1, HEIGHT - 1), "TX/RX: %.2f/%.2f Mbps" % (tx_value, rx_value), white)

    io = StringIO()
    image.writePng(io)
    io.seek(0)
    data = io.getvalue()
    io.close()
    return data


def draw_cpu_ts(hostname, start=None, end=None):
    fname = os.path.join(RRD_PREFIX, os.path.basename(hostname), "cpu", "virt_cpu_total.rrd")
    outfname = os.path.join(GRAPH_PREFIX, os.path.basename(hostname) + "-cpu.png")
    if not start:
        start = "-1d"
    start = str(start)
    if not end:
        end = "-20s"
    end = str(end)
    keyval = 'ns'
    if 'ds[value].index' in rrdtool.info(fname).keys():
        keyval = 'value'

    try:
        rrdtool.graph(outfname, "-s", "%s"%start, "-e", "%s"%end,
                      #"-t", "CPU usage",
                      "-v", "%",
                      #"--lazy",
                      "DEF:cpu=%s:%s:AVERAGE" % (fname, keyval),
                      "LINE1:cpu#00ff00:")
    except rrdtool.error, e:
        raise InternalError(str(e))

    return read_file(outfname)


def draw_cpu_ts_w(hostname):
    fname = os.path.join(RRD_PREFIX, os.path.basename(hostname), "cpu", "virt_cpu_total.rrd")
    outfname = os.path.join(GRAPH_PREFIX, os.path.basename(hostname) + "-cpu-weekly.png")

    try:
        rrdtool.graph(outfname, "-s", "-1w", "-e", "-20s",
                      #"-t", "CPU usage",
                      "-v", "%",
                      #"--lazy",
                      "DEF:cpu=%s:ns:AVERAGE" % fname,
                      "LINE1:cpu#00ff00:")
    except rrdtool.error, e:
        raise InternalError(str(e))

    return read_file(outfname)

def draw_net_ts(hostname, iface='eth0', start=None, end=None):
    fname = os.path.join(RRD_PREFIX, os.path.basename(hostname), "interface-" + iface, "if_octets.rrd")
#def draw_net_ts(hostname, start=None, end=None):
#    fname = os.path.join(RRD_PREFIX, os.path.basename(hostname), "interface-eth0", "if_octets.rrd")
    outfname = os.path.join(GRAPH_PREFIX, os.path.basename(hostname) + "-net.png")
    if not start:
        start = "-1d"
    start = str(start)
    if not end:
        end = "-20s"
    end = str(end)
    try:
        rrdtool.graph(outfname, "-s", "%s"%start, "-e", "%s"%end,
                  "-t", "%s" %iface,
                  "--units", "si",
                  "-v", "Bits/s",
                  #"--lazy",
                  "COMMENT:\t\t\tAverage network traffic\\n",
                  "DEF:rx=%s:rx:AVERAGE" % fname,
                  "DEF:tx=%s:tx:AVERAGE" % fname,
                  "CDEF:rxbits=rx,8,*",
                  "CDEF:txbits=tx,8,*",
                  "LINE1:rxbits#00ff00:Incoming",
                  "GPRINT:rxbits:AVERAGE:\t%4.0lf%sbps\t\g",
                  "LINE1:txbits#0000ff:Outgoing",
                  "GPRINT:txbits:AVERAGE:\t%4.0lf%sbps\\n")
    except rrdtool.error, e:
        raise InternalError(str(e))

    return read_file(outfname)

#def draw_net_ts(hostname, iface='eth0', start=None, end=None):
#    fname = os.path.join(RRD_PREFIX, os.path.basename(hostname), "interface-" + iface, "if_octets.rrd")
def draw_net_ts_w(hostname):
    fname = os.path.join(RRD_PREFIX, os.path.basename(hostname), "interface-eth0", "if_octets.rrd")
    outfname = os.path.join(GRAPH_PREFIX, os.path.basename(hostname) + "-net-weekly.png")
    try:
        rrdtool.graph(outfname, "-s", "-1w", "-e", "-20s",
                  #"-t", "Network traffic",
                  "--units", "si",
                  "-v", "Bits/s",
                  #"--lazy",
                  "COMMENT:\t\t\tAverage network traffic\\n",
                  "DEF:rx=%s:rx:AVERAGE" % fname,
                  "DEF:tx=%s:tx:AVERAGE" % fname,
                  "CDEF:rxbits=rx,8,*",
                  "CDEF:txbits=tx,8,*",
                  "LINE1:rxbits#00ff00:Incoming",
                  "GPRINT:rxbits:AVERAGE:\t%4.0lf%sbps\t\g",
                  "LINE1:txbits#0000ff:Outgoing",
                  "GPRINT:txbits:AVERAGE:\t%4.0lf%sbps\\n")
    except rrdtool.error, e:
        raise InternalError(str(e))

    return read_file(outfname)



def app(environ, start_response):
    graph = ""
    content_type = "text/plain"
    code = "200 OK"
    start = None
    end = None
    try:
        hostname, graph, startend, eth = environ["PATH_INFO"].strip("/").split("/", 4)
        graph_type = graph.split(".")[0]
        start, end = startend.split(',')
        try:
            if graph_type == "cpu-bar":
                graph = draw_cpu_bar(hostname)
            elif graph_type == "cpu-ts":
                graph = draw_cpu_ts(hostname, start, end)
            elif graph_type == "net-bar":
                graph = draw_net_bar(hostname)
            elif graph_type == "net-ts":
                graph = draw_net_ts(hostname, eth, start=start, end=end)
            elif graph_type == "cpu-ts-w":
                graph = draw_cpu_ts_w(hostname)
            elif graph_type == "net-ts-w":
                graph = draw_net_ts_w(hostname)
            content_type = "image/png"
        except InternalError:
            code = "500 INTERNAL SERVER ERROR"
        except NotFound:
            code = "404 NOT FOUND"
    except ValueError:
        try:
            hostname, graph, startend = environ["PATH_INFO"].strip("/").split("/", 3)
            graph_type = graph.split(".")[0]
            start, end = startend.split(',')
            try:
                if graph_type == "cpu-bar":
                    graph = draw_cpu_bar(hostname)
                elif graph_type == "cpu-ts":
                    graph = draw_cpu_ts(hostname, start, end)
                elif graph_type == "net-bar":
                    graph = draw_net_bar(hostname)
                elif graph_type == "net-ts":
                    graph = draw_net_ts(hostname, start=start, end=end)
                elif graph_type == "cpu-ts-w":
                    graph = draw_cpu_ts_w(hostname)
                elif graph_type == "net-ts-w":
                    graph = draw_net_ts_w(hostname)
                content_type = "image/png"
            except InternalError:
                code = "500 INTERNAL SERVER ERROR"
            except NotFound:
                code = "404 NOT FOUND"
        except ValueError:
            #No startend was provided
            try:
                hostname, graph = environ["PATH_INFO"].strip("/").split("/", 2)
                graph_type = graph.split(".")[0]

                try:
                    if graph_type == "cpu-bar":
                        graph = draw_cpu_bar(hostname)
                    elif graph_type == "cpu-ts":
                        graph = draw_cpu_ts(hostname, start, end)
                    elif graph_type == "net-bar":
                        graph = draw_net_bar(hostname)
                    elif graph_type == "net-ts":
                        graph = draw_net_ts(hostname, start=start, end=end)
                    elif graph_type == "cpu-ts-w":
                        graph = draw_cpu_ts_w(hostname)
                    elif graph_type == "net-ts-w":
                        graph = draw_net_ts_w(hostname)
                    content_type = "image/png"
                except Exception as e:
                    code = "500 INTERNAL SERVER ERROR: %s" %e
                except NotFound:
                    code = "404 NOT FOUND"
            except:
                code = "400 BAD REQUEST1"
        except Exception as e:
            code = "400 BAD REQUEST2 %s" %e
            raise Exception(e)
    except Exception as e:
        code = "400 BAD REQUEST2 %s" %e
        raise Exception(e)

    start_response(code,
                   [('Content-Type', content_type),
                    ('Content-Length', str(len(graph)))])
    return [graph]

#WSGIServer(app).run()

# vim: set ts=4 sts=4 sw=4 et ai:
