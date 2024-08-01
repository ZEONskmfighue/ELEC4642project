#!/usr/bin/python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.node import RemoteController
from mininet.cli import CLI
import time


class TopoStruc(Topo):
    def __init__(self):
        Topo.__init__(self)

        self.SwitchNum = 1  # 核心交换机数
        self.SwitchName = ['s' + str(x) for x in range(self.SwitchNum)]
        self.HostNum = 3  # 主机数
        self.HostName = ['h' + str(x + 1) for x in range(self.HostNum)]  # 确保主机名为 h1, h2, h3

        self.h_list = []
        self.s_list = []

        self.create_switch()
        self.create_host()
        self.add_links()

    def create_switch(self):
        for i in range(self.SwitchNum):
            dpid = "%02d" % i
            self.s_list.append(self.addSwitch(self.SwitchName[i], dpid=dpid))

    def create_host(self):
        for i in range(self.HostNum):
            ip = '10.0.0.%d' % (i + 1)
            self.h_list.append(self.addHost(self.HostName[i], ip=ip))

    def add_links(self):
        for i in range(self.HostNum):
            self.addLink(self.s_list[0], self.h_list[i])

    @staticmethod
    def run_iperf(client, server, duration):
        server.cmd('iperf -s &')  # 在后台启动iperf服务端
        time.sleep(1)  # 等待服务端启动
        client.cmd(f'iperf -c {server.IP()} -t {duration}')
        server.cmd('kill %iperf')  # 关闭iperf服务端


def create_net():
    topo = TopoStruc()
    c1 = RemoteController('RyuController', ip='127.0.0.1', port=6633, protocols='OpenFlow13')
    net = Mininet(topo=topo, controller=c1, link=TCLink, autoSetMacs=True, autoStaticArp=True)
    net.start()

    # 确保所有主机都正确获取
    h1 = net.get('h1')
    h2 = net.get('h2')
    h3 = net.get('h3')

    duration = 2

    # Start TCP traffic Generation
    TopoStruc.run_iperf(h1, h2, duration)
    TopoStruc.run_iperf(h1, h3, duration)
    TopoStruc.run_iperf(h2, h3, duration)

    CLI(net)
    net.stop()


if __name__ == '__main__':
    create_net()
