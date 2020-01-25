I2C Setup
```
#Turn on hardware support for I2C
sudo raspi-config

#I2C Tools (useful but just tools)
sudo apt install -y i2c-tools
sudo i2cdetect -y 1
```

Python Setup
```
# Package manager
sudo apt install -y python3-smbus
sudo apt install -y python3-pip
sudo apt install -y python3-pygame
sudo apt -y  install python-dev libatlas-base-dev
sudo pip3 install virtualenv 

# Grab the code
sudo apt install git
git clone https://github.com/asawho/airguitar
cd airguitar

#Start the environment up and install the packages
source venv/bin/activate
pip install smbus
pip install i2cdevice
pip install pygame
pip install rpi.gpio
pip install numpy
pip install pandas
```

Systemd Setup to have it Auto-Start
```
sudo cp airguitar.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable airguitar
sudo systemctl start airguitar
#See what it is doing
sudo journalctl -u airguitar.service
```