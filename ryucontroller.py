from ryu.base import app_manager  # Ryu应用程序管理基类
from ryu.ofproto import ofproto_v1_3  # OpenFlow v1.3协议定义
from ryu.controller.handler import set_ev_cls  # 事件处理器装饰器
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER  # 控制器状态常量
from ryu.controller import ofp_event  # OpenFlow事件定义
from ryu.lib.packet import packet, ethernet, ether_types  # 包处理库
from ryu.lib import hub  # Ryu的并发库
import subprocess
import json
from flask import Flask, jsonify
import threading


class FlowRules(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]  # 支持OpenFlow v1.3协议

    def __init__(self, *args, **kwargs):
        super(FlowRules, self).__init__(*args, **kwargs)
        self.mac_to_port = {}  # 存储MAC地址到端口的映射
        self.datapaths = {}  # 存储数据路径（交换机）的引用
#        self.monitor_thread = hub.spawn(self._monitor)  # 启动监控线程

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto  # 获取交换机使用的OpenFlow协议版本
        parser = datapath.ofproto_parser  # 获取交换机使用的协议解析器

        # 创建一个应用动作的指令
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)  # 发送流表修改消息到交换机

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath  # 获取交换机的数据路径对象
        ofproto = datapath.ofproto  # 获取OpenFlow协议对象
        parser = datapath.ofproto_parser  # 获取OpenFlow协议解析器

        # 安装一个表缺省流表项，将所有未匹配的流量发送到控制器
        match = parser.OFPMatch()  # 创建一个空的匹配字段
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg  # 获取事件消息
        datapath = msg.datapath  # 获取数据路径（交换机）
        ofproto = datapath.ofproto  # 获取OpenFlow协议对象
        parser = datapath.ofproto_parser  # 获取OpenFlow协议解析器
        in_port = msg.match['in_port']  # 获取数据包进入的端口

        pkt = packet.Packet(msg.data)  # 解析数据包
        eth = pkt.get_protocols(ethernet.ethernet)[0]  # 获取以太网协议数据

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:  # 忽略LLDP数据包
            return

        dst = eth.dst  # 获取目标MAC地址
        src = eth.src  # 获取源MAC地址

        dpid = datapath.id  # 获取交换机的ID
        self.mac_to_port.setdefault(dpid, {})  # 如果dpid不在字典中，则添加一个空字典

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # 学习源MAC地址，以避免下次泛洪
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]  # 获取目标MAC地址对应的端口
        else:
            out_port = ofproto.OFPP_FLOOD  # 如果未知目标MAC地址，则泛洪

        actions = [parser.OFPActionOutput(out_port)]  # 定义输出动作

        # 安装流表项以避免下次处理相同的数据包
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)  # 创建匹配字段
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data  # 获取数据

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)  # 发送PacketOut消息

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        body = ev.msg.body  # 获取端口统计信息
        self.logger.info('datapath         port     rx-pkts  rx-bytes rx-error tx-pkts  tx-bytes tx-error')
        self.logger.info('---------------- -------- -------- -------- -------- -------- -------- --------')
        for stat in sorted(body, key=lambda x: (x.port_no)):
            self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d',
                             ev.msg.datapath.id, stat.port_no,
                             stat.rx_packets, stat.rx_bytes, stat.rx_errors,
                             stat.tx_packets, stat.tx_bytes, stat.tx_errors)

    def request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto  # 获取OpenFlow协议对象
        parser = datapath.ofproto_parser  # 获取OpenFlow协议解析器

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)  # 创建端口统计请求消息
        datapath.send_msg(req)  # 发送请求消息

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, CONFIG_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath  # 获取数据路径（交换机）
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath  # 注册数据路径
        elif ev.state == 'DEAD_DISPATCHER':
            if datapath.id in self.datapaths:
                self.logger.info('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]  # 注销数据路径

    #def _monitor(self):
    #    while True:
    #        for dp in self.datapaths.values():
    #            self.request_stats(dp)  # 请求每个数据路径的统计信息
    #        hub.sleep(10)  # 每隔10秒请求一次

if __name__ == '__main__':
    app_manager.run_apps([FlowRules])

# 注：
# 1.此处注释掉了循环请求数据路径统计信息的函数，为调试方便，但实际不影响功能，注释或不注释都可；
# 2.在末尾添加了if语句，作用是创建一个ryucontroller 实例，以便于在flask文件中读取文件等操作，这一行可能可以删去也不影响使用，但是还是留着免得出事
