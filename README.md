# Psychite - Phison S11/PS3111 Tools

Tools for working with vendor-specific internals of SATA SSDs with Phison S11 controllers. Various features including reading firmware, writing firmware, and unpacking/repacking firmware files.

## Installation

```
git clone https://github.com/trulycrisp/psychite
cd psychite
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```
## Example Usage

The drive parameter should be a device path, for example `/dev/sg0` for Linux or `\\.\PhysicalDrive0` for Windows.

### Drive Information
```
example/drive_info.py <drive>
```

### Read Firmware From Drive
```
example/read_firmware.py <drive> firmware.bin
```

### Unpack Firmware
```
example/firmware_tool.py unpack firmware.bin firmware
```

### Repack Firmware
```
example/firmware_tool.py pack firmware firmware.bin
```

### Install Firmware
```
example/update_firmware.py firmware.bin <drive>
```

Read the scripts in the examples directory for further information.

