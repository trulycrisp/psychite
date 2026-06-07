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

### Linux
```
example/drive_info.py /dev/sg0
```

### Windows
```
example/drive_info.py \\.\PhysicalDrive0
```
