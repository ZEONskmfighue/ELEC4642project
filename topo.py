#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import Link, Intf, TCLink
from mininet.node import Controller, OVSSwitch, RemoteController, CPULimitedHost
from mininet.cli import CLI

class SimpleTopo(Topo):
    def __init__(self):
        Topo.__init__(self)  # 初始化Topo类

        # 核心交换机、汇聚交换机和主机的名称列表
        self.CoreName = ['c1']  # 核心交换机名列表
        self.AggrName = ['a1', 'a2']  # 汇聚交换机名列表
        self.HostName = ['h1', 'h2', 'h3', 'h4']  # 主机名列表

        # 初始化空列表以存储创建的主机和交换机
        self.HList = []
        self.CsList = []
        self.AsList = []

        self.create_switches()  # 调用创建交换机方法
        self.create_hosts()  # 调用创建主机方法
        self.add_links()  # 调用添加链路方法

    def create_switches(self):  # 创建交换机
        # Core 核心交换机
        core_count = 0  # 核心交换机计数器
        dpid = "00:00:00:00:00:00:00:%02d" % (1)  # 生成核心交换机的DPID（数据路径ID）
        # 添加核心交换机到交换机列表
        self.CsList.append(self.addSwitch(str(self.CoreName[core_count]), dpid=dpid))

        # Aggregation 汇聚交换机
        aggr_count = 0  # 汇聚交换机计数器
        for aggr in self.AggrName:
            dpid = "00:00:00:00:00:00:00:%02d" % (aggr_count + 2)  # 生成汇聚交换机的DPID
            # 添加汇聚交换机到交换机列表
            self.AsList.append(self.addSwitch(str(aggr), dpid=dpid))
            aggr_count += 1

    def create_hosts(self):  # 创建主机，并分配IP地址
        host_count = 0  # 主机计数器
        for host in self.HostName:
            ip = '10.0.0.%d' % (host_count + 1)  # 为每个主机生成IP地址
            # 添加主机到主机列表，并分配IP地址
            self.HList.append(self.addHost(str(host), ip=ip))
            host_count += 1

    def add_links(self):  # 添加链路
        # core - aggr 核心交换机到汇聚交换机的链路
        for aggr_switch in self.AsList:
            self.addLink(self.CsList[0], aggr_switch)  # 在核心交换机和汇聚交换机之间添加链路

        # aggr - host 汇聚交换机到主机的链路
        for i in range(len(self.HList)):
            # 将每个主机连接到对应的汇聚交换机
            self.addLink(self.AsList[i // 2], self.HList[i])

def create_network():  # 创建网络
    topo = SimpleTopo()  # 创建自定义拓扑实例
    # 创建Mininet实例，不使用默认控制器，设置自动分配MAC地址、静态ARP和主机CPU限制
    net = Mininet(topo=topo, controller=None, autoSetMacs=True, autoStaticArp=True, host=CPULimitedHost, link=TCLink)
    # 添加远程控制器，指定控制器名称、类型、IP地址、端口和协议
    net.addController('controller', controller=RemoteController, ip='127.0.0.1', port=6633, protocols="OpenFlow13")
    net.start()  # 启动网络
    CLI(net)  # 启动命令行接口（CLI）
    net.stop()  # 停止网络

# 注册拓扑，使其可以在Mininet中使用
topos = {'simpletopo': (lambda: SimpleTopo())}

if __name__ == '__main__':
    create_network()  # 如果此脚本作为主程序运行，则调用create_network函数创建网络
