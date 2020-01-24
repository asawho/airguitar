"""MMA8451 Driver."""
import time
from i2cdevice import Device, Register, BitField, _int_to_bytes
from i2cdevice.adapter import LookupAdapter, Adapter
import struct

__version__ = '0.0.1'

CHIP_ID = 0x1A
I2C_ADDRESS_DEFAULT = 0x1D
I2C_ADDRESS_ALTERNATE = 0x1C

# Internal constants:
_MMA8451_REG_OUT_X_MSB     = 0x01
_MMA8451_REG_SYSMOD        = 0x0B
_MMA8451_REG_WHOAMI        = 0x0D
_MMA8451_REG_XYZ_DATA_CFG  = 0x0E
_MMA8451_REG_PL_STATUS     = 0x10
_MMA8451_REG_PL_CFG        = 0x11
_MMA8451_REG_CTRL_REG1     = 0x2A
_MMA8451_REG_CTRL_REG2     = 0x2B
_MMA8451_REG_CTRL_REG4     = 0x2D
_MMA8451_REG_CTRL_REG5     = 0x2E
_MMA8451_DATARATE_MASK     = 0b111
_SENSORS_GRAVITY_EARTH     = 9.80665

# External user-facing constants:
PL_PUF           = 0      # Portrait, up, front
PL_PUB           = 1      # Portrait, up, back
PL_PDF           = 2      # Portrait, down, front
PL_PDB           = 3      # Portrait, down, back
PL_LRF           = 4      # Landscape, right, front
PL_LRB           = 5      # Landscape, right, back
PL_LLF           = 6      # Landscape, left, front
PL_LLB           = 7      # Landscape, left, back
RANGE_8G         = 0b10   # +/- 8g
RANGE_4G         = 0b01   # +/- 4g (default value)
RANGE_2G         = 0b00   # +/- 2g

class AccelerationAdapter(Adapter):
    def _decode(self, value):
        b = _int_to_bytes(value, 6)

       # Reconstruct signed 16-bit integers.
        x, y, z = struct.unpack('>hhh', b)
        x >>= 2
        y >>= 2
        z >>= 2
        
        return (x/1024.0*_SENSORS_GRAVITY_EARTH,
                y/1024.0*_SENSORS_GRAVITY_EARTH,
                z/1024.0*_SENSORS_GRAVITY_EARTH)

        #4g
        # return (x/2048.0*_SENSORS_GRAVITY_EARTH,
        #         y/2048.0*_SENSORS_GRAVITY_EARTH,
        #         z/2048.0*_SENSORS_GRAVITY_EARTH)

        # Scale values based on current sensor range to get proper units.
        # _range = self.range
        # if _range == RANGE_8G:
        #     return (x/1024.0*_SENSORS_GRAVITY_EARTH,
        #             y/1024.0*_SENSORS_GRAVITY_EARTH,
        #             z/1024.0*_SENSORS_GRAVITY_EARTH)
        # elif _range == RANGE_4G:
        #     return (x/2048.0*_SENSORS_GRAVITY_EARTH,
        #             y/2048.0*_SENSORS_GRAVITY_EARTH,
        #             z/2048.0*_SENSORS_GRAVITY_EARTH)
        # elif _range == RANGE_2G:
        #     return (x/4096.0*_SENSORS_GRAVITY_EARTH,
        #             y/4096.0*_SENSORS_GRAVITY_EARTH,
        #             z/4096.0*_SENSORS_GRAVITY_EARTH)
        # else:
        #     raise RuntimeError('Unexpected range!')

# Register('MMA8451_REG_OUT_X_MSB', _MMA8451_REG_OUT_X_MSB, fields=(
#     BitField('zero', 0x000000000000),
#     BitField('one', 0x000000000000),
#     BitField('two', 0x000000000000),
#     BitField('three', 0x000000000000),
#     BitField('four', 0x000000000000),
#     BitField('five', 0x000000000000),
# ), bit_width=8 * 6),

class MMA8451:
    def __init__(self, i2c_addr=I2C_ADDRESS_DEFAULT, i2c_dev=None):
        self._is_setup = False
        self._i2c_addr = i2c_addr
        self._i2c_dev = i2c_dev
        self._mma8451 = Device([I2C_ADDRESS_DEFAULT, I2C_ADDRESS_ALTERNATE], i2c_dev=self._i2c_dev, bit_width=8, registers=(
            Register('MMA8451_REG_XYZ_DATA_CFG', _MMA8451_REG_XYZ_DATA_CFG, fields=(
                BitField('range', 0b00000011, adapter=LookupAdapter({
                    '8g': 0b10,
                    '4g': 0b01,
                    '2g': 0b00
                })),
            )),
            Register('MMA8451_REG_OUT_X_MSB', _MMA8451_REG_OUT_X_MSB, fields=(
                BitField('value', 0xFFFFFFFFFFFF, adapter=AccelerationAdapter()),
            ), bit_width=8 * 6),
            Register('MMA8451_REG_PL_CFG', _MMA8451_REG_PL_CFG, fields=(
                BitField('value', 0xFF),
            )),
            Register('MMA8451_REG_CTRL_REG1', _MMA8451_REG_CTRL_REG1, fields=(
                BitField('value', 0xFF),
            )),
            Register('MMA8451_REG_CTRL_REG2', _MMA8451_REG_CTRL_REG2, fields=(
                BitField('value', 0xFF),
            )),
            Register('MMA8451_REG_CTRL_REG4', _MMA8451_REG_CTRL_REG4, fields=(
                BitField('value', 0xFF),
            )),
            Register('MMA8451_REG_CTRL_REG5', _MMA8451_REG_CTRL_REG5, fields=(
                BitField('value', 0xFF),
            )),
            Register('MMA8451_REG_PL_STATUS', _MMA8451_REG_PL_STATUS, fields=(
                BitField('value', 0xFF),
            )),
            Register('CHIP_ID', _MMA8451_REG_WHOAMI, fields=(
                BitField('id', 0xFF),
            ))
        ))

        self._mma8451.select_address(self._i2c_addr)

        #Verify chip ID
        try:
            chip = self._mma8451.get('CHIP_ID')
            if chip.id != CHIP_ID:
                raise RuntimeError("Unable to find mma8451 on 0x{:02x}, CHIP_ID returned {:02x}".format(self._i2c_addr, chip.id))
        except IOError:
            raise RuntimeError("Unable to find mma8451 on 0x{:02x}, IOError".format(self._i2c_addr))

        # Reset and wait for chip to be ready, if you read right away, you get an IOError, so just keep trying
        self._mma8451.set('MMA8451_REG_CTRL_REG2', value=0x40)
        while True:
            val = 0x40
            try:
                val = self._mma8451.get('MMA8451_REG_CTRL_REG2').value & 0x40
            except IOError:
                pass
            if val == 0:
                break        

        # Enable 4G range.
        self._mma8451.set('MMA8451_REG_XYZ_DATA_CFG', range='8g')        
        #High resolution
        self._mma8451.set('MMA8451_REG_CTRL_REG2', value=0x20)
        # DRDY on INT1
        self._mma8451.set('MMA8451_REG_CTRL_REG4', value=0x01)
        self._mma8451.set('MMA8451_REG_CTRL_REG5', value=0x01)
        # Turn on orientation config
        self._mma8451.set('MMA8451_REG_PL_CFG', value=0x40)
        # Activate at max rate, low noise mode
        self._mma8451.set('MMA8451_REG_CTRL_REG1', value=0x01 | 0x04)        

    def setup(self):
        pass

    @property
    def acceleration(self):
        return self._mma8451.get('MMA8451_REG_OUT_X_MSB').value
        # # pylint: disable=no-else-return
        # # This needs to be refactored when it can be tested
        # """Get the acceleration measured by the sensor.  Will return a 3-tuple
        # of X, Y, Z axis acceleration values in m/s^2.
        # """
        # # Read 6 bytes for 16-bit X, Y, Z values.
        # vals = self._mma8451.get('MMA8451_REG_OUT_X_MSB')
        # self._BUFFER[0]=vals.zero
        # self._BUFFER[1]=vals.one
        # self._BUFFER[2]=vals.two
        # self._BUFFER[3]=vals.three
        # self._BUFFER[4]=vals.four
        # self._BUFFER[5]=vals.five

        # # Reconstruct signed 16-bit integers.
        # x, y, z = struct.unpack('>hhh', _BUFFER)
        # x >>= 2
        # y >>= 2
        # z >>= 2
        # # Scale values based on current sensor range to get proper units.
        # _range = self.range
        # if _range == RANGE_8G:
        #     return (x/1024.0*_SENSORS_GRAVITY_EARTH,
        #             y/1024.0*_SENSORS_GRAVITY_EARTH,
        #             z/1024.0*_SENSORS_GRAVITY_EARTH)
        # elif _range == RANGE_4G:
        #     return (x/2048.0*_SENSORS_GRAVITY_EARTH,
        #             y/2048.0*_SENSORS_GRAVITY_EARTH,
        #             z/2048.0*_SENSORS_GRAVITY_EARTH)
        # elif _range == RANGE_2G:
        #     return (x/4096.0*_SENSORS_GRAVITY_EARTH,
        #             y/4096.0*_SENSORS_GRAVITY_EARTH,
        #             z/4096.0*_SENSORS_GRAVITY_EARTH)
        # else:
        #     raise RuntimeError('Unexpected range!')

    @property
    def orientation(self):
        """Get the orientation of the MMA8451.  Will return a value of:
         - PL_PUF: Portrait, up, front
         - PL_PUB: Portrait, up, back
         - PL_PDF: Portrait, down, front
         - PL_PDB: Portrait, down, back
         - PL_LRF: Landscape, right, front
         - PL_LRB: Landscape, right, back
         - PL_LLF: Landscape, left, front
         - PL_LLB: Landscape, left, back
        """
        return self._mma8451.get('MMA8451_REG_PL_STATUS').value & 0x07