# Copyright (C) 2016 Huang MaChi at Chongqing University
# of Posts and Telecommunications, China.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import Link, Intf, TCLink
from mininet.topo import Topo

import logging
import os
import time
from subprocess import Popen
from multiprocessing import Process


class Hungry(Topo):
	"""
		Class of Hungry Topology.
	"""
	def __init__(self):
		# Init Topo
		Topo.__init__(self)

		# Add hosts and switches
		self.h1 = self.addHost( 'h1' )
		self.h2 = self.addHost( 'h2' )
		self.h3 = self.addHost( 'h3' )
		self.h4 = self.addHost( 'h4' )
		self.h5 = self.addHost( 'h5' )
		self.h6 = self.addHost( 'h6' )
		self.s1 = self.addSwitch( 's1' )

		# Add links
		self.addLink(self.h1, self.s1, bw=10, max_queue_size=1000)
		self.addLink(self.h2, self.s1, bw=10, max_queue_size=1000)
		self.addLink(self.h3, self.s1, bw=10, max_queue_size=1000)
		self.addLink(self.s1, self.h4, bw=10, max_queue_size=1000)
		self.addLink(self.s1, self.h5, bw=10, max_queue_size=1000)
		self.addLink(self.s1, self.h6, bw=10, max_queue_size=1000)

	def set_ovs_protocol_13(self):
		"""
			Set the OpenFlow version for switches.
		"""
		cmd = "sudo ovs-vsctl set bridge s1 protocols=OpenFlow13"
		os.system(cmd)

def install_proactive(topo):
	# s1
	# ARP
	for i in range(1, 7):
		cmd = "ovs-ofctl add-flow s1 -O OpenFlow13 'table=0,idle_timeout=0,hard_timeout=0,priority=1,arp,nw_dst=10.0.0.%d,actions=output:%d'" % (i, i)
		os.system(cmd)
	# IP
	for i in range(1, 7):
		cmd = "ovs-ofctl add-flow s1 -O OpenFlow13 'table=0,idle_timeout=0,hard_timeout=0,priority=1,ip,nw_dst=10.0.0.%d,actions=output:%d'" % (i, i)
		os.system(cmd)

def monitor_devs_ng(fname="./bwmng.txt", interval_sec=0.1):
	"""
		Use bwm-ng tool to collect interface transmit rate statistics.
		bwm-ng Mode: rate;
		interval time: 1s.
	"""
	cmd = "sleep 1; bwm-ng -t %s -o csv -u bits -T rate -C ',' > %s" %  (interval_sec * 1000, fname)
	Popen(cmd, shell=True).wait()

def traffic_generation(net, topo):
	"""
		Generate traffics and test the performance of the network.
	"""
	# 1. Start bwm-ng to monitor throughput.
	monitor = Process(target = monitor_devs_ng, args = ('./results/bwmng.txt', 1.0))
	monitor.start()

	# 2. Start iperf. (Elephant flows)
	client = net.get('h1')
	server1 = net.get('h4')
	server1.cmd("iperf -s > /dev/null &" )   # Its statistics is useless, just throw away.
	client.cmd("iperf -c %s -t 120 > /dev/null &" % server1.IP())   # Its statistics is useless, just throw away.

	time.sleep(30)

	server2 = net.get('h5')
	server2.cmd("iperf -s > /dev/null &" )   # Its statistics is useless, just throw away.
	client.cmd("iperf -c %s -t 90 > /dev/null &" % server2.IP())   # Its statistics is useless, just throw away.

	time.sleep(30)

	server3 = net.get('h6')
	server3.cmd("iperf -s > /dev/null &" )   # Its statistics is useless, just throw away.
	client.cmd("iperf -c %s -t 60 > /dev/null &" % server3.IP())   # Its statistics is useless, just throw away.

	# 3. The experiment is going on.
	time.sleep(65)

	# 4. Shut down.
	monitor.terminate()
	os.system('killall bwm-ng')
	os.system('killall iperf')

def test_corruption():
	"""
		Create network topology and generate traffics.
	"""
	topo = Hungry()
	net = Mininet(topo=topo, link=TCLink, controller=None, autoSetMacs=True)
	net.start()

	# Set the OpenFlow version for switches as 1.3.0.
	topo.set_ovs_protocol_13()

	# Install proactive flow entries
	install_proactive(topo)

	# Generate traffics and test the performance of the network.
	traffic_generation(net, topo)

	# CLI(net)
	net.stop()


if __name__ == '__main__':
	setLogLevel('info')
	if os.getuid() != 0:
		logging.debug("You are NOT root")
	elif os.getuid() == 0:
		test_corruption()
