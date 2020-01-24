I2C Setup
```
#Turn on hardware support
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
```

Requirements
```
pip install smbus
pip install i2cdevice
pip install pygame
```
machine learning
```
sudo apt -y  install python-dev libatlas-base-dev
```
```
pip install rpi.gpio
pip install numpy
pip install pandas
```