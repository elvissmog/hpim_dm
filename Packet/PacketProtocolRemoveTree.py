from Packet.PacketProtocolSetTree import PacketProtocolInstallTree
'''
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|        Upstream Neighbor Address (Encoded Unicast Format)     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Reserved    |  Num Groups   |          Hold Time            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
'''
class PacketProtocolUninstallTree(PacketProtocolInstallTree):
    PIM_TYPE = "UNINSTALL"

    def __init__(self, source, group, counter):
        super().__init__(source, group, 0, 0, counter)

    @classmethod
    def parse_bytes(cls, data: bytes):
        source = data["SOURCE"]
        group = data["GROUP"]
        sn = data["SN"]
        return cls(source, group, sn)
