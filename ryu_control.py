from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types
from ryu.lib import hub

class ProjectTopoController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ProjectTopoController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}  # 存储MAC地址到端口的映射
        self.datapaths = {}  # 存储所有数据路径（交换机）的信息
        self.monitor_thread = hub.spawn(self._monitor)  # 启动监控线程

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath  # 获取交换机的数据路径对象
        ofproto = datapath.ofproto  # 获取协议版本
        parser = datapath.ofproto_parser  # 获取协议解析器

        # 安装表未命中流表项
        match = parser.OFPMatch()  # 匹配所有流量
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]  # 动作为将流量发送到控制器
        self.add_flow(datapath, 0, match, actions)  # 添加流表项
        self.datapaths[datapath.id] = datapath  # 注册交换机

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto  # 获取协议版本
        parser = datapath.ofproto_parser  # 获取协议解析器

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]  # 指定动作
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)  # 构建流表项消息
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)  # 构建流表项消息
        datapath.send_msg(mod)  # 发送流表项消息到交换机

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes", ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg  # 获取消息对象
        datapath = msg.datapath  # 获取数据路径对象
        ofproto = datapath.ofproto  # 获取协议版本
        parser = datapath.ofproto_parser  # 获取协议解析器
        in_port = msg.match['in_port']  # 获取输入端口

        pkt = packet.Packet(msg.data)  # 解析数据包
        eth = pkt.get_protocols(ethernet.ethernet)[0]  # 获取以太网协议

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return  # 忽略LLDP数据包

        dst = eth.dst  # 目的MAC地址
        src = eth.src  # 源MAC地址

        dpid = format(datapath.id, "d").zfill(16)  # 获取交换机ID，并格式化为16位
        self.mac_to_port.setdefault(dpid, {})  # 初始化MAC到端口的映射表

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # 学习源MAC地址到端口的映射，以避免下次再进行洪泛
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]  # 如果目的MAC地址已知，获取对应的端口
        else:
            out_port = ofproto.OFPP_FLOOD  # 否则进行洪泛

        actions = [parser.OFPActionOutput(out_port)]  # 设置动作为输出到目的端口

        # 安装流表项以避免下次再触发packet_in事件
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)  # 设置匹配条件
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)  # 添加流表项
                return
            else:
                self.add_flow(datapath, 1, match, actions)  # 添加流表项

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data  # 如果没有缓冲区ID，则获取数据

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)  # 构建PacketOut消息
        datapath.send_msg(out)  # 发送PacketOut消息

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        body = ev.msg.body  # 获取消息体
        self.logger.info('datapath         port     rx-pkts  rx-bytes rx-error tx-pkts  tx-bytes tx-error')
        self.logger.info('---------------- -------- -------- -------- -------- -------- -------- --------')
        for stat in sorted(body, key=lambda x: (x.port_no)):
            self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d',
                             ev.msg.datapath.id, stat.port_no,
                             stat.rx_packets, stat.rx_bytes, stat.rx_errors,
                             stat.tx_packets, stat.tx_bytes, stat.tx_errors)  # 记录端口统计信息

    def request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto  # 获取协议版本
        parser = datapath.ofproto_parser  # 获取协议解析器

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)  # 构建端口统计请求
        datapath.send_msg(req)  # 发送请求

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, CONFIG_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath  # 获取数据路径对象
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath  # 注册交换机
        elif ev.state == 'DEAD_DISPATCHER':
            if datapath.id in self.datapaths:
                self.logger.info('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]  # 注销交换机

