import random
import traceback
from threading import Timer, RLock
import socket
import time
import logging
import netifaces

from Interface import Interface
from Neighbor import Neighbor
import Main
from tree.protocol_globals import MSG_FORMAT, HELLO_HOLD_TIME_TIMEOUT
from ReliableMsgTransmission import ReliableMessageTransmission

from Packet.Packet import Packet
from Packet.ReceivedPacket import ReceivedPacket
if MSG_FORMAT == "BINARY":
    from Packet.PacketProtocolHelloOptions import PacketNewProtocolHelloHoldtime as PacketProtocolHelloHoldtime, \
        PacketNewProtocolHelloCheckpointSN as PacketProtocolHelloCheckpointSN
    from Packet.PacketProtocolHello import PacketNewProtocolHello as PacketProtocolHello
    from Packet.PacketProtocolHeader import PacketNewProtocolHeader as PacketProtocolHeader
    from Packet.PacketProtocolSync import PacketNewProtocolSyncEntry as PacketProtocolHelloSyncEntry,\
        PacketNewProtocolSync as PacketProtocolHelloSync
    from Packet.PacketProtocolInterest import PacketNewProtocolNoInterest as PacketProtocolNoInterest,\
        PacketNewProtocolInterest as PacketProtocolInterest
    from Packet.PacketProtocolSetTree import PacketNewProtocolUpstream as PacketProtocolUpstream
    from Packet.PacketProtocolRemoveTree import PacketNewProtocolNoLongerUpstream as PacketProtocolNoLongerUpstream
    from Packet.PacketProtocolAck import PacketNewProtocolAck as PacketProtocolAck
else:
    from Packet.PacketProtocolHelloOptions import PacketProtocolHelloHoldtime, PacketProtocolHelloCheckpointSN
    from Packet.PacketProtocolHello import PacketProtocolHello
    from Packet.PacketProtocolHeader import PacketProtocolHeader
    from Packet.PacketProtocolSync import PacketProtocolHelloSync
    from Packet.PacketProtocolSetTree import PacketProtocolUpstream
    from Packet.PacketProtocolInterest import PacketProtocolNoInterest, PacketProtocolInterest
    from Packet.PacketProtocolSync import PacketProtocolHelloSyncEntry
    from Packet.PacketProtocolRemoveTree import PacketProtocolNoLongerUpstream
    from Packet.PacketProtocolAck import PacketProtocolAck


class InterfaceProtocol(Interface):
    MCAST_GRP = '224.0.0.13'

    MAX_SEQUENCE_NUMBER = (2**32-1)#45 <- test with lower MAXIMUM_SEQUENCE_NUMBER

    HELLO_PERIOD = 30
    TRIGGERED_HELLO_PERIOD = 5

    LOGGER = logging.getLogger('protocol.Interface')

    def __init__(self, interface_name: str, vif_index: int):
        self.interface_logger = logging.LoggerAdapter(InterfaceProtocol.LOGGER, {'vif': vif_index,
                                                                                 'interfacename': interface_name})

        # Generate BootTime
        self.time_of_boot = int(time.time())

        # Regulate transmission of Hello messages
        self.hello_timer = None

        # protocol neighbors
        self._had_neighbors = False
        self.neighbors = {}
        self.neighbors_lock = RLock()

        # reliable transmission buffer
        self.reliable_transmission_buffer = {} # Key: ID da msg ; value: ReliableMsgTransmission
        self.reliable_transmission_lock = RLock()

        # sequencer for msg reliability
        self.sequencer = 0
        self.sequencer_lock = RLock()

        # SOCKET
        ip_interface = netifaces.ifaddresses(interface_name)[netifaces.AF_INET][0]['addr']
        self.ip_interface = ip_interface

        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_PIM)

        # allow other sockets to bind this port too
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # explicitly join the multicast group on the interface specified
        #s.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(Interface.MCAST_GRP) + socket.inet_aton(ip_interface))
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                     socket.inet_aton(Interface.MCAST_GRP) + socket.inet_aton(ip_interface))
        s.setsockopt(socket.SOL_SOCKET, 25, str(interface_name + '\0').encode('utf-8'))

        # set socket output interface
        s.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(ip_interface))

        # set socket TTL to 1
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, 1)

        # don't receive outgoing packets
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)

        super().__init__(interface_name, s, s, vif_index)
        #super()._enable()
        self.force_send_hello()

    def get_ip(self):
        """
        Get IP of this interface
        """
        return self.ip_interface

    def _receive(self, raw_bytes):
        """
        Interface received a new control packet
        """
        if raw_bytes:
            packet = ReceivedPacket(raw_bytes, self)
            self.PKT_FUNCTIONS[packet.payload.get_pim_type()](self, packet)

    def send(self, data: Packet, group_ip: str=MCAST_GRP):
        """
        Send a new packet destined to group_ip IP
        """
        super().send(data=data.bytes(), group_ip=group_ip)

    def get_sequence_number(self):
        """
        Get the new sequence number SN to be transmitted in a new control message
        This method will increment the last used sequence number and return it
        It also returns the current BootTime
        """
        with self.sequencer_lock:
            self.sequencer += 1

            if self.sequencer == InterfaceProtocol.MAX_SEQUENCE_NUMBER:
                self.time_of_boot = int(time.time())
                self.sequencer = 1
                self.clear_reliable_transmission()
                self.force_send_hello()

            return (self.time_of_boot, self.sequencer)

    def get_checkpoint_sn(self):
        """
        Get the CheckpointSN to be transmitted in a new Hello message
        """
        print("A ENTRAR CHECK_SN")
        with self.neighbors_lock:
            with self.sequencer_lock:
                with self.reliable_transmission_lock:
                    time_of_boot = self.time_of_boot
                    checkpoint_sn = self.sequencer

                    for rt in self.reliable_transmission_buffer.values():
                        (msg_boot_time, msg_checkpoint_sn) = rt.get_sequence_number()
                        if msg_boot_time == time_of_boot and checkpoint_sn > msg_checkpoint_sn:
                            checkpoint_sn = msg_checkpoint_sn

                    print("A SAIR CHECK_SN")
                    return (time_of_boot, checkpoint_sn)

    #Random interval for initial Hello message on bootup or triggered Hello message to a rebooting neighbor
    def force_send_hello(self):
        """
        Force the transmission of a new Hello message
        """
        if self.hello_timer is not None:
            self.hello_timer.cancel()

        hello_timer_time = random.uniform(0, self.TRIGGERED_HELLO_PERIOD)
        self.hello_timer = Timer(hello_timer_time, self.send_hello)
        self.hello_timer.start()

    def send_hello(self):
        """
        Send a new Hello message
        Include in it the HelloHoldTime and CheckpointSN
        """
        self.hello_timer.cancel()

        pim_payload = PacketProtocolHello()
        pim_payload.add_option(PacketProtocolHelloHoldtime(holdtime=4 * self.HELLO_PERIOD))

        with self.neighbors_lock:
            with self.sequencer_lock:
                with self.reliable_transmission_lock:
                    (bt, checkpoint_sn) = self.get_checkpoint_sn()
                    if bt == self.time_of_boot:
                        pim_payload.add_option(PacketProtocolHelloCheckpointSN(checkpoint_sn))

                ph = PacketProtocolHeader(pim_payload, boot_time=self.time_of_boot)
        packet = Packet(payload=ph)
        self.send(packet)

        # reschedule hello_timer
        self.hello_timer = Timer(self.HELLO_PERIOD, self.send_hello)
        self.hello_timer.start()

    def remove(self):
        """
        Remove this interface
        Clear all state
        """
        self.hello_timer.cancel()
        self.hello_timer = None

        # send pim_hello timeout message
        pim_payload = PacketProtocolHello()
        pim_payload.add_option(PacketProtocolHelloHoldtime(holdtime=HELLO_HOLD_TIME_TIMEOUT))
        ph = PacketProtocolHeader(pim_payload, boot_time=self.time_of_boot)
        packet = Packet(payload=ph)
        self.send(packet)

        super().remove()
        for n in self.neighbors.values():
            n.remove_neighbor_state()
        self.neighbors.clear()
        self.clear_reliable_transmission()

    def snapshot_multicast_routing_table(self):
        """
        Create a new snapshot
        This method will return the current BootTime, SnapshotSN and all trees to be included in Sync messages
        """
        with Main.kernel.rwlock.genWlock():
            with self.sequencer_lock:
                (snapshot_bt, snapshot_sn) = self.get_sequence_number()

                trees_to_sync = Main.kernel.snapshot_multicast_routing_table(self.vif_index)  # type: dict
                tree_to_sync_in_msg_format = {}

                for (source_group, state) in trees_to_sync.items():
                    tree_to_sync_in_msg_format[source_group] = PacketProtocolHelloSyncEntry(source_group[0], source_group[1], state.metric_preference, state.route_metric)

                return (snapshot_bt, snapshot_sn, tree_to_sync_in_msg_format)

    ##############################################
    # Check neighbor status
    ##############################################
    def get_tree_state(self, source_group):
        """
        Get Upstream and Interest state regarding a given tree...
        Regarding Upstream this method will return the Upstream neighbor that offers the best RPC metric
        Regarding Interest this method will return "Interested/True" if at least one neighbor is interested
            or "NotInterested" if all neighbors are not interested in traffic regarding (source_group) tree
        """
        interest_state = False
        upstream_state = None
        for n in list(self.neighbors.values()):
            (neighbor_interest_state, neighbor_upstream_state) = n.get_tree_state(tree=source_group)
            if not interest_state and neighbor_interest_state:
                interest_state = neighbor_interest_state

            if neighbor_upstream_state is not None:
                if upstream_state is None:
                    upstream_state = neighbor_upstream_state
                elif neighbor_upstream_state.is_better_than(upstream_state):
                    upstream_state = neighbor_upstream_state

        print("GET_TREE_STATE_INTERFACE INTEREST:", interest_state)
        print("GET_TREE_STATE_INTERFACE UPSTREAM:", upstream_state)
        return (interest_state, upstream_state)

    def remove_tree_state(self, source_ip, group_ip):
        """
        Remove tree state regarding a given (Source_IP, Group_IP) tree
        """
        for n in list(self.neighbors.values()):
            n.remove_tree_state(source_ip, group_ip)

    # Used to show list of neighbors in CLI interfaces
    def get_neighbors(self):
        """
        Get all neighbors
        """
        with self.neighbors_lock:
            return self.neighbors.values()


    def did_all_neighbors_acked(self, neighbors_that_acked: set):
        """
        Verify if all neighbor have acknowledged a given message
        Compare if all neighbors that are being monitored are present in neighbors_that_acked set
        """
        return neighbors_that_acked >= self.neighbors.keys()

    def is_neighbor(self, neighbor_ip):
        """
        Verify if neighbor_ip is considered a neighbor
        """
        return neighbor_ip in self.neighbors

    def remove_neighbor(self, ip):
        """
        Remove known neighbor
        """
        with self.neighbors_lock:
            if ip not in self.neighbors:
                return
            self.neighbors.pop(ip)

            # verifiar todas as arvores
            print("REMOVER ANTES RECHECK")
            Main.kernel.recheck_all_trees(self.vif_index)
            print("REMOVER DEPOIS RECHECK")

    '''
    def change_interface(self):
        # check if ip change was already applied to interface
        old_ip_address = self.ip_interface
        new_ip_interface = netifaces.ifaddresses(self.interface_name)[netifaces.AF_INET][0]['addr']
        if old_ip_address == new_ip_interface:
            return
        
        self._send_socket.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(new_ip_interface))

        self._recv_socket.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP,
                     socket.inet_aton(Interface.MCAST_GRP) + socket.inet_aton(old_ip_address))

        self._recv_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                                     socket.inet_aton(Interface.MCAST_GRP) + socket.inet_aton(new_ip_interface))

        self.ip_interface = new_ip_interface
    '''

    ###########################################
    # Recv packets
    ###########################################
    def new_neighbor(self, neighbor_ip, boot_time, detected_via_non_sync_msg=True):
        """
        New neighbor detected... start monitoring it and start synchronization
        """
        with self.neighbors_lock:
            self.neighbors[neighbor_ip] = Neighbor(self, neighbor_ip, 120, boot_time, self.time_of_boot)

            if detected_via_non_sync_msg:
                self.neighbors[neighbor_ip].start_sync_process()

    def receive_hello(self, packet):
        """
        Received an Hello packet
        """
        ip = packet.ip_header.ip_src
        boot_time = packet.payload.boot_time
        print("ip = ", ip)
        options = packet.payload.payload.get_options()
        hello_hold_time = options["HOLDTIME"].holdtime
        checkpoint_sn = 0
        if "CHECKPOINT_SN" in options:
            checkpoint_sn = options["CHECKPOINT_SN"].checkpoint_sn
        self.interface_logger.debug('Received Hello message with HelloHoldTime: ' + str(hello_hold_time) +
                                    '; CheckpointSN: ' + str(checkpoint_sn) + ' from neighbor ' + ip)

        with self.neighbors_lock:
            if ip in self.neighbors:
                self.neighbors[ip].recv_hello(boot_time, hello_hold_time, checkpoint_sn)
            else:
                self.new_neighbor(ip, boot_time, True)

    def receive_sync(self, packet):
        """
        Received an Sync packet
        """
        ip = packet.ip_header.ip_src
        boot_time = packet.payload.boot_time

        pkt_hs = packet.payload.payload  # type: PacketProtocolHelloSync

        # Process Sync msg
        my_boot_time = pkt_hs.neighbor_boot_time
        if my_boot_time != self.time_of_boot:
            return

        # All information in Sync msg
        sync_sn = pkt_hs.sync_sequence_number
        upstream_trees = pkt_hs.upstream_trees
        hello_options = pkt_hs.get_hello_options()
        neighbor_sn = pkt_hs.my_snapshot_sn
        my_sn = pkt_hs.neighbor_snapshot_sn
        master_flag = pkt_hs.master_flag
        more_flag = pkt_hs.more_flag

        self.interface_logger.debug('Received Sync message with BootTime: ' + str(boot_time) +
                                    '; NeighborBootTime: ' + str(my_boot_time) +
                                    '; MySnapshotSN: ' + str(neighbor_sn) +
                                    '; NeighborSnapshotSN: ' + str(my_sn) +
                                    '; SyncSN: ' + str(sync_sn) +
                                    '; Master flag: ' + str(master_flag) +
                                    '; More flag: ' + str(more_flag) +
                                    ' from neighbor ' + ip)

        with self.neighbors_lock:
            if ip not in self.neighbors:
                self.new_neighbor(ip, boot_time, detected_via_non_sync_msg=False)

            self.neighbors[ip].recv_sync(upstream_trees, my_sn, neighbor_sn, boot_time, sync_sn, master_flag, more_flag, my_boot_time, hello_options)

    def receive_interest(self, packet):
        """
        Received an Interest packet
        """
        neighbor_source_ip = packet.ip_header.ip_src
        boot_time = packet.payload.boot_time

        pkt_jt = packet.payload.payload  # type: PacketProtocolInterest

        # Process Interest msg
        source_group = (pkt_jt.source, pkt_jt.group)
        sequence_number = pkt_jt.sequence_number

        self.interface_logger.debug('Received Interest message with BootTime: ' + str(boot_time) +
                                    '; Tree: ' + str(source_group) +
                                    '; SN: ' + str(sequence_number) +
                                    ' from neighbor ' + neighbor_source_ip)

        # check neighbor existence
        with self.neighbors_lock:
            neighbor = self.neighbors.get(neighbor_source_ip, None)
            if neighbor is None:
                self.new_neighbor(neighbor_source_ip, boot_time)
                return

            try:
                if neighbor.recv_reliable_packet(sequence_number, source_group, boot_time):
                    if source_group not in neighbor.tree_metric_state:
                        neighbor.tree_interest_state[source_group] = True
                        Main.kernel.recv_interest_msg(source_group, self)
                    else:
                        neighbor.tree_interest_state[source_group] = True
                        neighbor.tree_metric_state.pop(source_group, None)
                        Main.kernel.recv_upstream_msg(source_group, self)
            except:
                traceback.print_exc()

    def receive_no_interest(self, packet):
        """
        Received a NoInterest packet
        """
        neighbor_source_ip = packet.ip_header.ip_src
        boot_time = packet.payload.boot_time

        pkt_jt = packet.payload.payload  # type: PacketProtocolNoInterest

        # Process NoInterest msg
        source_group = (pkt_jt.source, pkt_jt.group)
        sequence_number = pkt_jt.sequence_number

        self.interface_logger.debug('Received NoInterest message with BootTime: ' + str(boot_time) +
                                    '; Tree: ' + str(source_group) +
                                    '; SN: ' + str(sequence_number) +
                                    ' from neighbor ' + neighbor_source_ip)

        # check neighbor existence
        with self.neighbors_lock:
            neighbor = self.neighbors.get(neighbor_source_ip, None)
            if neighbor is None:
                self.new_neighbor(neighbor_source_ip, boot_time)
                return

            try:
                if neighbor.recv_reliable_packet(sequence_number, source_group, boot_time):
                    if source_group not in neighbor.tree_metric_state:
                        neighbor.tree_interest_state[source_group] = False
                        Main.kernel.recv_interest_msg(source_group, self)
                    else:
                        neighbor.tree_interest_state[source_group] = False
                        neighbor.tree_metric_state.pop(source_group, None)
                        Main.kernel.recv_upstream_msg(source_group, self)
            except:
                traceback.print_exc()

    def receive_i_am_upstream(self, packet):
        """
        Received an IamUpstream packet
        """
        from tree.metric import AssertMetric
        neighbor_source_ip = packet.ip_header.ip_src
        boot_time = packet.payload.boot_time
        pkt_jt = packet.payload.payload # type: PacketProtocolUpstream

        # Process IamUpstream msg
        source_group = (pkt_jt.source, pkt_jt.group)
        sequence_number = pkt_jt.sequence_number

        metric_preference = pkt_jt.metric_preference
        metric = pkt_jt.metric
        received_metric = AssertMetric(metric_preference=metric_preference, route_metric=metric, ip_address=neighbor_source_ip)

        self.interface_logger.debug('Received IamUpstream message with BootTime: ' + str(boot_time) +
                                    '; Tree: ' + str(source_group) +
                                    '; SN: ' + str(sequence_number) +
                                    '; MetricPreference: ' + str(metric_preference) +
                                    '; Metric: ' + str(metric) +
                                    ' from neighbor ' + neighbor_source_ip)

        # check neighbor existence
        with self.neighbors_lock:
            neighbor = self.neighbors.get(neighbor_source_ip, None)
            if neighbor is None:
                self.new_neighbor(neighbor_source_ip, boot_time)
                return

            try:
                if neighbor.recv_reliable_packet(sequence_number, source_group, boot_time):
                    neighbor.tree_interest_state.pop(source_group, None)
                    neighbor.tree_metric_state[source_group] = received_metric
                    Main.kernel.recv_upstream_msg(source_group, self)
            except:
                traceback.print_exc()

    def receive_i_am_no_longer_upstream(self, packet):
        """
        Received an IamNoLongerUpstream packet
        """
        neighbor_source_ip = packet.ip_header.ip_src
        boot_time = packet.payload.boot_time
        pkt_jt = packet.payload.payload

        # Process IamNoLongerUpstream msg
        source_group = (pkt_jt.source, pkt_jt.group)
        sequence_number = pkt_jt.sequence_number

        self.interface_logger.debug('Received IamNoLongerUpstream message with BootTime: ' + str(boot_time) +
                                    '; Tree: ' + str(source_group) +
                                    '; SN: ' + str(sequence_number) +
                                    ' from neighbor ' + neighbor_source_ip)

        # check neighbor existence
        with self.neighbors_lock:
            neighbor = self.neighbors.get(neighbor_source_ip, None)
            if neighbor is None:
                self.new_neighbor(neighbor_source_ip, boot_time)
                return

            try:
                if neighbor.recv_reliable_packet(sequence_number, source_group, boot_time):
                    neighbor.tree_interest_state.pop(source_group, None)
                    neighbor.tree_metric_state.pop(source_group, None)
                    Main.kernel.recv_upstream_msg(source_group, self)
            except:
                traceback.print_exc()


    def receive_ack(self, packet):
        """
        Received an Ack packet
        """
        neighbor_source_ip = packet.ip_header.ip_src
        neighbor_boot_time = packet.payload.boot_time
        pkt_ack = packet.payload.payload  # type: PacketProtocolAck

        # Process Ack msg
        source_group = (pkt_ack.source, pkt_ack.group)
        my_boot_time = pkt_ack.neighbor_boot_time
        my_snapshot_sn = pkt_ack.neighbor_snapshot_sn
        neighbor_snapshot_sn = pkt_ack.my_snapshot_sn
        sequence_number = pkt_ack.sequence_number

        self.interface_logger.debug('Received Ack message with BootTime: ' + str(neighbor_boot_time) +
                                    '; NeighborBootTime: ' + str(my_boot_time) +
                                    '; MySnapshotSN: ' + str(neighbor_snapshot_sn) +
                                    '; NeighborSnapshotSN: ' + str(my_snapshot_sn) +
                                    '; Tree: ' + str(source_group) +
                                    '; SN: ' + str(sequence_number) +
                                    ' from neighbor ' + neighbor_source_ip)


        # check neighbor existence
        with self.neighbors_lock:
            neighbor = self.neighbors.get(neighbor_source_ip, None) # type: Neighbor
            if neighbor is None:
                self.new_neighbor(neighbor_source_ip, neighbor_boot_time)
                return

            with self.sequencer_lock:
                with self.reliable_transmission_lock:
                    if not neighbor.recv_ack(my_boot_time, neighbor_boot_time, my_snapshot_sn, neighbor_snapshot_sn):
                        return

                    #if my_boot_time != self.time_of_boot:
                    #    return

                    reliable_transmission = self.reliable_transmission_buffer.get(source_group, None)
                    if reliable_transmission is not None:
                        reliable_transmission.receive_ack(neighbor_source_ip, my_boot_time, sequence_number)


    PKT_FUNCTIONS = {
        PacketProtocolHello.PIM_TYPE:            receive_hello,
        PacketProtocolHelloSync.PIM_TYPE:        receive_sync,
        PacketProtocolUpstream.PIM_TYPE:         receive_i_am_upstream,
        PacketProtocolNoLongerUpstream.PIM_TYPE: receive_i_am_no_longer_upstream,
        PacketProtocolInterest.PIM_TYPE:         receive_interest,
        PacketProtocolNoInterest.PIM_TYPE:       receive_no_interest,
        PacketProtocolAck.PIM_TYPE:              receive_ack,
    }


    ########################################################################
    # Message Transmission
    ########################################################################
    def get_reliable_message_transmission(self, tree):
        """
        Get object used to monitor the reliable transmission of messages regarding a given tree
        """
        with self.reliable_transmission_lock:
            reliable_msg_transmission = self.reliable_transmission_buffer.get(tree, None)

            if reliable_msg_transmission is None:
                reliable_msg_transmission = ReliableMessageTransmission(self)
                self.reliable_transmission_buffer[tree] = reliable_msg_transmission

            return reliable_msg_transmission

    def send_i_am_upstream(self, source, group, rpc):
        """
        Send a new IamUpstream message
        """
        tree = (source, group)
        with self.sequencer_lock:
            with self.reliable_transmission_lock:
                self.get_reliable_message_transmission(tree).send_i_am_upstream(source, group, rpc)

    def send_i_am_no_longer_upstream(self, source, group):
        """
        Send a new IamNoLongerUpstream message
        """
        tree = (source, group)
        with self.sequencer_lock:
            with self.reliable_transmission_lock:
                self.get_reliable_message_transmission(tree).send_i_am_no_longer_upstream(source, group)

    def send_interest(self, source, group, dst):
        """
        Send a new Interest message
        """
        tree = (source, group)
        with self.sequencer_lock:
            with self.reliable_transmission_lock:
                self.get_reliable_message_transmission(tree).send_interest(source, group, dst)

    def send_no_interest(self, source, group, dst):
        """
        Send a new NoInterest message
        """
        tree = (source, group)
        with self.sequencer_lock:
            with self.reliable_transmission_lock:
                self.get_reliable_message_transmission(tree).send_no_interest(source, group, dst)

    def neighbor_start_synchronization(self, neighbor_ip, my_snapshot_bt, my_snapshot_sn):
        """
        Neighbor started a new synchronization... consider all trees included in the snapshot to be Acknowledged
        (all packets transmitted with a lower BootTime or lower SN compared to SnapshotSN will be considered to have been
        acknowledged by it)
        """
        with self.reliable_transmission_lock:
            for rmt in self.reliable_transmission_buffer.values():
                rmt.receive_ack(neighbor_ip, my_snapshot_bt, my_snapshot_sn)

    def cancel_all_messages(self, tree):
        """
        Cancel the reliable monitoring of all messages regarding a given tree
        """
        with self.reliable_transmission_lock:
            if tree in self.reliable_transmission_buffer:
                self.reliable_transmission_buffer[tree].cancel_all_messages()

    def cancel_interest_message(self, tree, neighbor_ip):
        """
        Cancel the reliable monitoring of all interest messages regarding a given tree
        """
        with self.reliable_transmission_lock:
            if tree in self.reliable_transmission_buffer:
                self.reliable_transmission_buffer[tree].cancel_message_unicast(neighbor_ip)

    def cancel_upstream_message(self, tree):
        """
        Cancel the reliable monitoring of all upstream messages regarding a given tree
        """
        with self.reliable_transmission_lock:
            if tree in self.reliable_transmission_buffer:
                self.reliable_transmission_buffer[tree].cancel_message_multicast()

    def clear_reliable_transmission(self):
        """
        Cancel the reliable monitoring of all messages regarding all trees
        """
        with self.reliable_transmission_lock:
            for rmt in self.reliable_transmission_buffer.values():
                rmt.cancel_all_messages()

    '''
    def cancel_message(self, tree):
        with self.reliable_transmission_lock:
            reliable_packet = self.reliable_transmission_buffer.get(tree, None)
            if reliable_packet is not None:
                reliable_packet.cancel_message()
    '''
