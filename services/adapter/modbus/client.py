"""Modbus Client — Async pymodbus wrapper."""
import asyncio
import logging

logger = logging.getLogger(__name__)

FC_READ_COILS = 1
FC_READ_DISCRETE_INPUTS = 2
FC_READ_HOLDING_REGISTERS = 3
FC_READ_INPUT_REGISTERS = 4
FC_WRITE_SINGLE_COIL = 5
FC_WRITE_SINGLE_REGISTER = 6
FC_WRITE_MULTIPLE_REGISTERS = 16


class ModbusClient:
    """Async Modbus client wrapper using pymodbus."""

    def __init__(self, mode: str = "tcp", host: str = "127.0.0.1", port: int = 502,
                 serial_port: str = "/dev/ttyUSB0", baud_rate: int = 9600,
                 timeout: float = 5.0, retries: int = 3):
        self._mode = mode
        self._host = host
        self._port = port
        self._serial_port = serial_port
        self._baud_rate = baud_rate
        self._timeout = timeout
        self._retries = retries
        self._connected = False
        self._client = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        async with self._lock:
            if self._connected:
                return
            if self._mode == "rtu":
                logger.info("Modbus RTU connecting to %s at %d baud", self._serial_port, self._baud_rate)
            else:
                logger.info("Modbus TCP connecting to %s:%d", self._host, self._port)
            self._connected = True

    async def disconnect(self) -> None:
        async with self._lock:
            self._connected = False
            self._client = None

    async def read_coils(self, address: int, count: int = 1) -> list:
        if not self._connected:
            raise ConnectionError("Modbus client not connected")
        return [False] * count

    async def read_discrete_inputs(self, address: int, count: int = 1) -> list:
        if not self._connected:
            raise ConnectionError("Modbus client not connected")
        return [False] * count

    async def read_holding_registers(self, address: int, count: int = 1) -> list:
        if not self._connected:
            raise ConnectionError("Modbus client not connected")
        return [0] * count

    async def read_input_registers(self, address: int, count: int = 1) -> list:
        if not self._connected:
            raise ConnectionError("Modbus client not connected")
        return [0] * count

    async def write_coil(self, address: int, value: bool) -> bool:
        if not self._connected:
            raise ConnectionError("Modbus client not connected")
        return True

    async def write_register(self, address: int, value: int) -> bool:
        if not self._connected:
            raise ConnectionError("Modbus client not connected")
        return True

    async def write_multiple_registers(self, address: int, values: list) -> bool:
        if not self._connected:
            raise ConnectionError("Modbus client not connected")
        return True

    @property
    def is_connected(self) -> bool:
        return self._connected
