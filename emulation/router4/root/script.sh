cd hpim_dm

tcpdump -i eth1 -w /hosthome/Desktop/test_newproto/test_loop/TestResults/Router4_Router5.pcap &

python3 Run.py -stop
python3 Run.py -start
python3 Run.py -t R4 10.3.3.7
python3 Run.py -aiigmp eth0
python3 Run.py -aiigmp eth1
python3 Run.py -aiigmp eth2
python3 Run.py -ai eth0
python3 Run.py -ai eth1
python3 Run.py -ai eth2
python3 Run.py -v
