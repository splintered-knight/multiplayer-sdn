import os

GAME_QUEUE = int(os.getenv("GAME_QUEUE", "1"))

if GAME_QUEUE not in (0, 1):
    raise ValueError("GAME_QUEUE must be 0 or 1")
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet, ipv4, udp, tcp


class GameController(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(GameController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        datapath.send_msg(parser.OFPFlowMod(
            datapath=datapath,
            priority=0,
            match=parser.OFPMatch(),
            instructions=[
                parser.OFPInstructionActions(
                    ofproto.OFPIT_APPLY_ACTIONS,
                    [
                        parser.OFPActionOutput(
                            ofproto.OFPP_CONTROLLER,
                            ofproto.OFPCML_NO_BUFFER
                        )
                    ]
                )
            ]
        ))

    def add_flow(self, datapath, priority, match, actions):
        parser = datapath.ofproto_parser

        datapath.send_msg(parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=[
                parser.OFPInstructionActions(
                    datapath.ofproto.OFPIT_APPLY_ACTIONS,
                    actions
                )
            ]
        ))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth is None or eth.ethertype == 0x88cc:
            return

        src = eth.src
        dst = eth.dst
        dpid = datapath.id

        # Learn the source MAC address and its switch port.
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        # Find the output port for the destination MAC.
        out_port = self.mac_to_port[dpid].get(
            dst, ofproto.OFPP_FLOOD
        )

        ip = pkt.get_protocol(ipv4.ipv4)
        udp_pkt = pkt.get_protocol(udp.udp)
        tcp_pkt = pkt.get_protocol(tcp.tcp)

        if out_port == ofproto.OFPP_FLOOD:
            actions = [
                parser.OFPActionOutput(ofproto.OFPP_FLOOD)
            ]

        else:
            priority = 10
            queue_id = 0
            match = None

            # Match UDP traffic using its IP addresses and UDP ports.
            if ip and udp_pkt:
                match = parser.OFPMatch(
                    in_port=in_port,
                    eth_type=0x0800,
                    ip_proto=17,
                    ipv4_src=ip.src,
                    ipv4_dst=ip.dst,
                    udp_src=udp_pkt.src_port,
                    udp_dst=udp_pkt.dst_port
                )

                # Give game traffic higher priority and Queue 1.
                if (
                    udp_pkt.src_port == 5000
                    or udp_pkt.dst_port == 5000
                ):
                    priority = 100
                    queue_id = GAME_QUEUE

            # Match TCP traffic using its IP addresses and TCP ports.
            elif ip and tcp_pkt:
                match = parser.OFPMatch(
                    in_port=in_port,
                    eth_type=0x0800,
                    ip_proto=6,
                    ipv4_src=ip.src,
                    ipv4_dst=ip.dst,
                    tcp_src=tcp_pkt.src_port,
                    tcp_dst=tcp_pkt.dst_port
                )

            # Match other IPv4 traffic by IP protocol and addresses.
            elif ip:
                if ip.proto not in (6, 17):
                    match = parser.OFPMatch(
                        in_port=in_port,
                        eth_type=0x0800,
                        ip_proto=ip.proto,
                        ipv4_src=ip.src,
                        ipv4_dst=ip.dst
                    )

            # Match ARP and other Ethernet traffic separately.
            else:
                match = parser.OFPMatch(
                    in_port=in_port,
                    eth_type=eth.ethertype,
                    eth_src=src,
                    eth_dst=dst
                )

            # Install a rule only when a sufficiently specific match exists.
            if match is not None:
                actions = [
                    parser.OFPActionSetQueue(queue_id),
                    parser.OFPActionOutput(out_port)
                ]

                self.add_flow(
                    datapath,
                    priority,
                    match,
                    actions
                )
            else:
                actions = [
                    parser.OFPActionSetQueue(0),
                    parser.OFPActionOutput(out_port)
                ]

        # Forward the current packet as well as installing its future rule.
        data = None

        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        datapath.send_msg(parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        ))

 
