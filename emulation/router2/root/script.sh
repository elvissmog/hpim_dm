rm -rf MulticastRouting/
cp -rf /hosthome/Desktop/new_protocol2/ MulticastRouting/
cd MulticastRouting
#pip-3.2 install --index-url=https://pypi.python.org/simple/ -r requirements.txt

python3 Run.py -stop
python3 Run.py -start
python3 Run.py -t R2 10.3.3.7
python3 Run.py -aiigmp eth0
python3 Run.py -aiigmp eth1
python3 Run.py -ai eth0
python3 Run.py -ai eth1
python3 Run.py -v
