import struct
import socket
###########################################################################################################
# JSON FORMAT
###########################################################################################################
class PacketProtocolHelloSyncEntry():
    def __init__(self, source, group, metric_preference, metric):
        self.source = source
        self.group = group
        self.metric = metric
        self.metric_preference = metric_preference

    def bytes(self):
        msg = {"SOURCE": self.source,
               "GROUP": self.group,
               "METRIC": self.metric,
               "METRIC_PREFERENCE": self.metric_preference,
              }

        return msg

    @staticmethod
    def parse_bytes(data: bytes):
        source = data["SOURCE"]
        group = data["GROUP"]
        metric = data["METRIC"]
        metric_preference = data["METRIC_PREFERENCE"]
        return PacketProtocolHelloSyncEntry(source, group, metric_preference, metric)


class PacketProtocolHelloSync():
    PIM_TYPE = "SYNC"

    def __init__(self, my_snapshot_sn, neighbor_snapshot_sn, sync_sn, upstream_trees=[],
                 master_flag=False, more_flag=False, neighbor_boot_time=0):
        self.sync_sequence_number = sync_sn
        self.my_snapshot_sn = my_snapshot_sn
        self.neighbor_snapshot_sn = neighbor_snapshot_sn
        self.neighbor_boot_time = neighbor_boot_time
        self.upstream_trees = upstream_trees
        self.master_flag = master_flag
        self.more_flag = more_flag


    def bytes(self) -> bytes:
        trees = []
        for entry in self.upstream_trees:
            trees.append(entry.bytes())

        msg = {"SYNC_SN": self.sync_sequence_number,
               "MY_SNAPSHOT_SN": self.my_snapshot_sn,
               "NEIGHBOR_SNAPSHOT_SN": self.neighbor_snapshot_sn,
               "NEIGHBOR_BOOT_TIME": self.neighbor_boot_time,
               "TREES": trees,
               "MASTER_FLAG": self.master_flag,
               "MORE_FLAG": self.more_flag,
              }

        return msg

    def parse_bytes(data: bytes):
        trees = []
        for entry in data["TREES"]:
            trees.append(PacketProtocolHelloSyncEntry.parse_bytes(entry))

        sync_sn = data["SYNC_SN"]
        my_snapshot_sn = data["MY_SNAPSHOT_SN"]
        neighbor_snapshot_sn = data["NEIGHBOR_SNAPSHOT_SN"]
        neighbor_boot_time = data["NEIGHBOR_BOOT_TIME"]
        master_flag = data["MASTER_FLAG"]
        more_flag = data["MORE_FLAG"]

        return PacketProtocolHelloSync(my_snapshot_sn, neighbor_snapshot_sn, sync_sn, trees, master_flag, more_flag,
                                       neighbor_boot_time)


###########################################################################################################
# BINARY FORMAT
###########################################################################################################
'''
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Tree Source IP                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Tree Group IP                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Metric Preference                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                            Metric                             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
'''
class PacketNewProtocolSyncEntry():
    PIM_HDR_SYNC_ENTRY = "! 4s 4s L L"
    PIM_HDR_SYNC_ENTRY_LEN = struct.calcsize(PIM_HDR_SYNC_ENTRY)


    def __init__(self, source, group, metric_preference, metric):
        if type(source) not in (str, bytes) or type(group) not in (str, bytes):
            raise Exception
        if type(source) is bytes:
            source = socket.inet_ntoa(source)
        if type(group) is bytes:
            group = socket.inet_ntoa(group)

        self.source = source
        self.group = group
        self.metric = metric
        self.metric_preference = metric_preference

    def __len__(self):
        return PacketNewProtocolSyncEntry.PIM_HDR_SYNC_ENTRY_LEN

    def bytes(self):
        msg = struct.pack(PacketNewProtocolSyncEntry.PIM_HDR_SYNC_ENTRY, socket.inet_aton(self.source),
                          socket.inet_aton(self.group), self.metric_preference, self.metric)
        return msg

    @staticmethod
    def parse_bytes(data: bytes):
        (source, group, metric_preference, metric) = struct.unpack(
            PacketNewProtocolSyncEntry.PIM_HDR_SYNC_ENTRY,
            data[:PacketNewProtocolSyncEntry.PIM_HDR_SYNC_ENTRY_LEN])
        return PacketNewProtocolSyncEntry(source, group, metric_preference, metric)


'''
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         MySnapshotSN                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      NeighborSnapshotSN                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       NeighborBootTime                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|M|m|                        Sync SN                            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Trees (equivalent to multiple IamUpstream messages)       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
'''
class PacketNewProtocolSync:
    PIM_TYPE = 1

    PIM_HDR_INSTALL_WITHOUT_TREES = "! L L L L"
    PIM_HDR_INSTALL_WITHOUT_TREES_LEN = struct.calcsize(PIM_HDR_INSTALL_WITHOUT_TREES)

    def __init__(self, my_snapshot_sn, neighbor_snapshot_sn, sync_sn, upstream_trees,
                 master_flag=False, more_flag=False, neighbor_boot_time=0):
        self.my_snapshot_sn = my_snapshot_sn
        self.neighbor_snapshot_sn = neighbor_snapshot_sn
        self.neighbor_boot_time = neighbor_boot_time
        self.sync_sequence_number = sync_sn
        self.master_flag = master_flag
        self.more_flag = more_flag
        self.upstream_trees = upstream_trees

    def add_tree(self, t):
        self.upstream_trees.append(t)

    def bytes(self) -> bytes:
        flags_and_sync_sn = (self.master_flag << 31) | (self.more_flag << 30) | self.sync_sequence_number

        msg = struct.pack(PacketNewProtocolSync.PIM_HDR_INSTALL_WITHOUT_TREES, self.my_snapshot_sn,
                          self.neighbor_snapshot_sn, self.neighbor_boot_time, flags_and_sync_sn)

        for t in self.upstream_trees:
            msg += t.bytes()

        return msg

    def __len__(self):
        return len(self.bytes())

    @staticmethod
    def parse_bytes(data: bytes):
        (my_snapshot_sn, neighbor_snapshot_sn, neighbor_boot_time, flags_and_sync_sn) = \
            struct.unpack(PacketNewProtocolSync.PIM_HDR_INSTALL_WITHOUT_TREES,
                          data[:PacketNewProtocolSync.PIM_HDR_INSTALL_WITHOUT_TREES_LEN])

        sync_sn = flags_and_sync_sn & 0x3FFFFFFF
        master_flag = flags_and_sync_sn >> 31
        more_flag = (flags_and_sync_sn & 0x4FFFFFFF) >> 30
        data = data[PacketNewProtocolSync.PIM_HDR_INSTALL_WITHOUT_TREES_LEN:]
        sync_msg = PacketNewProtocolSync(my_snapshot_sn, neighbor_snapshot_sn, sync_sn, [], master_flag=master_flag,
                                         more_flag=more_flag, neighbor_boot_time=neighbor_boot_time)
        while data != b'':
            tree_msg = PacketNewProtocolSyncEntry.parse_bytes(data)

            sync_msg.add_tree(tree_msg)
            data = data[len(tree_msg):]

        return sync_msg
