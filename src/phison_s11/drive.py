"""Phison S11 drive functionality."""

import base64
import dataclasses
import enum
import pathlib
import struct
import time
from typing import ClassVar, Self

from phison_s11 import algorithm as s11_algorithm
from phison_s11 import firmware as s11_firmware
from phison_s11 import flash as s11_flash
from phison_s11 import info_block as s11_info_block
from phison_s11 import system_info as s11_system_info
from phison_s11.ata import command as ata_command
from phison_s11.ata import drive as ata_drive
from phison_s11.ata import identify as ata_identify

_VUC_UNLOCK_KEYS: dict[int, bytes] = {
    1: base64.b85decode(
        b"n~NYKsn^15@+6~0d6S|wYr)gwSDpZ6z#_8O^f4GGFB2D+KO-_ePv<AKgHSwTljUBd3x*g"
        b"$!S`kf6<ocAk7oHEp!{GpE*s<?%0Kz5ST@1Xz=i(UxiBVM|Ixd)5a#U`s3DU{$ecz5yt8"
        b")h6bX~{ohe8XdDD#D{aytSmr@XibaEwDB8O+?^%5Sn@|@1zrgAh@Jnq^$KnDI*Uj8R_&`"
        b"}DA1(*D_9uRG+R_E`!2O)I0?Z1~6_EwU`7l7?n=z*ADi%>4@o*b6s@~*o+W*Z3+lbwWWP"
        b"=DsRvTh$?I^D3wy@j(dMo)gMe4p;RxTy|c&i*eYA$?rG",
    ),
    2: base64.b85decode(
        b"u&6pWEYNB)jzws*JDd~{2<F4=n)*?>!z%0XR0Yv9K5^diDS2Tqpdo2LGNMP~DlbP6>3nx"
        b"|eF8`uN^jm;r(vnu_M4-f1OXXS)y+?5g}3P4w0il~Wou{**!TsqaI<VHf_ntsO?YJ@IMZ"
        b"vjD&ACHAKHH7MwPkw&~(37J5Dp3Ywu0cFHk*YF_v&-QYT8=Zbgi5>6GG|4|!$G2G!Ld4I"
        b"t<-=c>exX@0gUI{SmITXOvsgR$})v0d^r7XQGa9C4GQOv2|b*ZR785cKZIL}qLti*<_r)"
        b"=;V8GF?W8zso>Rr>PBzZ$l>srbVY`!VUpONcq;rt^w!M",
    ),
    3: base64.b85decode(
        b"ju8+aSe=`)xqz1?`1TCm4Yx|WMw=Uk77ohAhl@}J=aQj)h>7G7?tdf8IVa`n*3#Oem1a<"
        b"QiBKvB=MNiNwGcHs6nP9=ePoaPZ^T-2X!Os)e9?8932B1^m|W{jNKW%)gaK=>f6=!w{6d"
        b"+!&6c^Kcg{6FL?d8<a3dE@7Nb0ddtY{?XL?Ld#fVVW@k=clH@buF{rxr#-g>&cUfnf&QN"
        b"l+Lc9&;X+Vop}!*xOjK>iyZK+N+y9hf1Oz^TWs=?+p<B~9)PMj8VuY@a@7z#90zYWzq@z"
        b"f<B1U#b(Hg=1KzNH+@CqQva&9JoA0tC$3(W8@DB+o+|h",
    ),
    4: base64.b85decode(
        b"pO&QLI~H8XXzx#<fW)+T%SnZ!yPg2Tqt0nDn#A7Q&?MS!MV6&6?TImwwn%{8&%J5W=(R>"
        b"i<+3K9B_2w*C274M(BC#lDj^`;i@eku1||te`FCf}@JWnX-%b?YKIpic^03*TkNPQx^M("
        b"py+Yo^d0`Bb4Xx%h}nUEqK+;q~+XzHspTVUp&t0TLi%|5ryv@9`Q+g}KOb|b$?=vE4J;P"
        b";~k-!=E7A;<<fiGO^<WKoW@8wmtMdnk-CRxZHnP5HC5?BJ7lf2F16l;aXP?o7u{J!6b&M"
        b"gH(5fQ&Q@fQnK-?*{q3s(nAQ_*j!6vH5Sc7IY6-hPal`",
    ),
    5: base64.b85decode(
        b"u0<DAv6Lvu?0ha1ho$Jw6<8+XQ#DTGOqmbhui9cJ`8~FM?Rlq%BXO4g%ZLyTK5yuc2V$-"
        b"hW7W4K<%F>|{G|-@*~`6`QUjSXOQp-Uu>(q*DaB29=SCxHb1B9Su$b~Dv$mFvzuMnl5_J"
        b"p1S=k0ap<hbNi8z)1b;ZEI3)Fw8u2x8T4toJIEqyZU%{ZnDcniF~-O#rN4dY{x++ScyQB"
        b"8U~jZ>!(LFj%Tx^=@&{r^ADdba+QMNf9|bAXrO1ybgGqftSb#S|26f~073q%}mmE;Rndx"
        b"rE>5HUfo=UzZ~dYZ+`YkSf%J0ou#tsfm1sFQW<z3`-q1",
    ),
}


class VUCFeature(enum.IntEnum):
    """Vendor-unique command type identifiers.

    Attributes:
        RESTART: Soft restart.
        RESET_SMART: Reset SMART.
        JUMP: Jump to code in RAM.
        PREFORMAT: Format/initialise System Area (SA).
        READ_FLASH: Read raw flash page.
        READ_SRAM: Read controller SRAM.
        SYSTEM_INFO: Read system information.
        FLASH_ID: Read flash ID for one CE.
        FLASH_ID_ALL: Read flash ID for all CEs.
        WRITE_FLASH: Write raw flash page.
        ERASE_FLASH: Erase raw flash block.
        SET_PARAMETER: Set VUC parameter data for next command.
        WRITE_INFO_BLOCK: Write drive information.
        ERASE_ALL_BLOCK: Erase all blocks.
        READ_INFO_BLOCK: Read drive information.
        CHECK_CRC: Verify CRC of code in RAM.
        VERIFY_FLASH: Read back firmware from flash.
        PROGRAM_PRAM: Write code to instruction RAM.
        PROGRAM_FLASH_HEADER: Write firmware header to flash.
        WRITE_REGISTER: Write memory value.
        READ_REGISTER: Read memory value.
        SEND_SEED: Send firmware metadata/seed.
        PROGRAM_FLASH_CODE: Write firmware code to flash.
        ONFI_PARAMETER_PAGE: Read ONFI parameter page.
        MAX_BAD_PER_PLANE: Read maximum number of bad blocks per plane.
        PROGRAM_PRAM_ICODE: Write code to SRAM.
        VERIFY_PRAM_ICODE: Read back code from SRAM.
        VUC_UNLOCK_START: Start VUC unlock sequence.
        VUC_UNLOCK_READ: Read unlock challenge.
        VUC_UNLOCK_WRITE: Write unlock response.
        VUC_LOCK: Re-lock VUC access.
        READ_PRODUCT_HISTORY: Read product history.
        WRITE_PRODUCT_HISTORY: Write product history.
        BLOCK_MAP: Read map of flash blocks in first CE of channel.

    """

    RESTART = 0x1
    RESET_SMART = 0x2
    JUMP = 0xF
    PREFORMAT = 0x8
    READ_FLASH = 0x10
    READ_SRAM = 0x12
    SYSTEM_INFO = 0x13
    FLASH_ID = 0x14
    FLASH_ID_ALL = 0x15
    WRITE_FLASH = 0x20
    ERASE_FLASH = 0x22
    SET_PARAMETER = 0x24
    WRITE_INFO_BLOCK = 0x25
    ERASE_ALL_BLOCK = 0x26
    READ_INFO_BLOCK = 0x28
    CHECK_CRC = 0x30
    VERIFY_FLASH = 0x31
    PROGRAM_PRAM = 0x40
    PROGRAM_FLASH_HEADER = 0x41
    WRITE_REGISTER = 0x60
    READ_REGISTER = 0x61
    SEND_SEED = 0x80
    PROGRAM_FLASH_CODE = 0x82
    ONFI_PARAMETER_PAGE = 0xA7
    MAX_BAD_PER_PLANE = 0xA8
    PROGRAM_PRAM_ICODE = 0xBD
    VERIFY_PRAM_ICODE = 0xBE
    VUC_UNLOCK_START = 0xC4
    VUC_UNLOCK_READ = 0xC5
    VUC_UNLOCK_WRITE = 0xC6
    VUC_LOCK = 0xC7
    READ_PRODUCT_HISTORY = 0xDA
    WRITE_PRODUCT_HISTORY = 0xDB
    BLOCK_MAP = 0xFB


class Mode(enum.Enum):
    """Drive operating mode.

    Attributes:
        ROM: ROM/bootstrap mode.
        BURNER: Firmware burner mode.
        NORMAL: Normal operation mode.

    """

    ROM = enum.auto()
    BURNER = enum.auto()
    NORMAL = enum.auto()


class FlashIDManufacturer(enum.IntEnum):
    """JEDEC JEP106 NAND flash manufacturer IDs.

    Attributes:
        SPANSION: Spansion.
        FUJITSU: Fujitsu.
        RENESAS: Renesas.
        STMICRO: STMicroelectronics.
        MICRON: Micron.
        SANDISK: SanDisk.
        SMIC: SMIC.
        QIMONDA: Qimonda.
        INTEL: Intel.
        ESMT_POWERCHIP: ESMT/Powerchip.
        TOSHIBA: Toshiba.
        YMTC: YMTC.
        HYNIX: SK Hynix.
        SPECTEK: SpecTek.
        MACRONIX: Macronix.
        ESMT_MIRA_PSC: ESMT/MIRA/PSC.
        SAMSUNG: Samsung.
        WINBOND: Winbond.

    """

    SPANSION = 1
    FUJITSU = 4
    RENESAS = 7
    STMICRO = 32
    MICRON = 44
    SANDISK = 69
    SMIC = 74
    QIMONDA = 81
    INTEL = 137
    ESMT_POWERCHIP = 146
    TOSHIBA = 152
    YMTC = 155
    HYNIX = 173
    SPECTEK = 181
    MACRONIX = 194
    ESMT_MIRA_PSC = 200
    SAMSUNG = 236
    WINBOND = 239


class FlashIDCellType(enum.IntEnum):
    """Flash cell type.

    Attributes:
        SLC: Single-level cell.
        MLC: Multi-level cell.
        TLC: Triple-level cell.
        QLC: Quad-level cell.

    """

    SLC = 0
    MLC = 1
    TLC = 2
    QLC = 3


class FlashPageMagic(enum.IntEnum):
    """Magic values in flash page metadata.

    Attributes:
        FIRMWARE_HEADER: Firmware header page.
        FIRMWARE_CODE: Firmware code page.
        SYSTEM_UNIT_HEADER: System unit header page.
        SYSTEM_UNIT_DATA: System unit data page.
        BLOCK_MAP: Block map page.
        PRODUCT_HISTORY: Product history page.
        ERROR_UNIT: Error unit page.

    """

    FIRMWARE_HEADER = 0x31113111
    FIRMWARE_CODE = 0x55AA55AA
    SYSTEM_UNIT_HEADER = 0xFFA00000
    SYSTEM_UNIT_DATA = 0x44505354
    BLOCK_MAP = 0x3FB10200
    PRODUCT_HISTORY = 0x3FB10400
    ERROR_UNIT = 0xFFD00000


class BlockType(enum.Enum):
    """Block allocation status in the FTL block map.

    Attributes:
        FTL_FREE: Free FTL block.
        FTL_OPEN_PSLC: FTL open (non-full) data pseudo-SLC block.
        FTL_OPEN_NATIVE_MLC: FTL open (non-full) data native MLC block.
        FTL_OPEN_NATIVE: FTL open (non-full) data block for non-MLC native modes
            (SLC, TLC, QLC).
        FTL_CLOSED_PSLC: FTL closed (full) data pseudo-SLC block.
        FTL_CLOSED_NATIVE_MLC: FTL closed (full) data native MLC block.
        FTL_CLOSED_NATIVE: FTL closed (full) data block for non-MLC native modes
            (SLC, TLC, QLC).
        FTL_META: FTL metadata (e.g. L2P).
        SYSTEM: System block not managed by the FTL.

    """

    FTL_FREE = 0x4
    FTL_OPEN_PSLC = 0x9
    FTL_OPEN_NATIVE_MLC = 0xA
    FTL_OPEN_NATIVE = 0xB
    FTL_CLOSED_PSLC = 0x11
    FTL_CLOSED_NATIVE_MLC = 0x12
    FTL_CLOSED_NATIVE = 0x13
    FTL_META = 0x21
    SYSTEM = 0x41


@dataclasses.dataclass(frozen=True)
class FlashID:
    """Parsed NAND flash identification data.

    Attributes:
        SIZE: Raw flash ID data size in bytes.
        manufacturer: JEDEC manufacturer ID.
        cell_type: Cell type (SLC/MLC/TLC/QLC).

    """

    SIZE: ClassVar[int] = 8

    manufacturer: FlashIDManufacturer
    cell_type: FlashIDCellType

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Parse VUC Flash ID output.

        Args:
            data: Raw data.

        Returns:
            Parsed Flash ID.

        """
        # Parse JEDEC JEP106 manufacturer
        manufacturer: FlashIDManufacturer = FlashIDManufacturer(data[0])

        cell_type: FlashIDCellType
        if (
            manufacturer == FlashIDManufacturer.YMTC
            and data[1:5] == b"\xd5\x58\x8d\x20"
        ):
            cell_type = FlashIDCellType.QLC
        else:
            cell_type = FlashIDCellType((data[2] >> 2) & 0b11)

        return cls(manufacturer, cell_type)


def _register_size(data_size: int) -> int:
    reg_sizes: list[int] = [1, 2, 4]

    return next(x for x in sorted(reg_sizes, reverse=True) if data_size >= x)


def _vuc_unlock_derive_seed(data: bytes) -> int:
    buffer: bytearray = bytearray(32)

    for i, x in enumerate(data):
        buffer[i % len(buffer)] ^= x

    return int.from_bytes(buffer[:4], "little")


class Drive(ata_drive.Drive):
    """Phison S11 drive."""

    # Common maximum data size of many commands
    _CMD_MAX_SECTORS: int = 128
    _CMD_MAX_SIZE: int = _CMD_MAX_SECTORS * ata_command.SECTOR_SIZE

    DLMC_SEGMENT_SECTORS: int = _CMD_MAX_SECTORS

    def __init__(self, path: pathlib.Path) -> None:
        """Open S11 drive.

        Args:
            path: Path to drive.

        """
        super().__init__(path)
        self.vuc_unlock()

    def _vuc_set_ap_key(self) -> None:
        self.command(
            ata_command.CommandRegisters(
                count=0x6F,
                lba=0xFAEFFE,
                command=ata_command.Command.STANDBY_IMMEDIATE,
            ),
        )

    def _vuc_unset_ap_key(self) -> None:
        self.command(
            ata_command.CommandRegisters(
                count=0x90,
                lba=0x51001,
                command=ata_command.Command.STANDBY_IMMEDIATE,
            ),
        )

    def vuc(
        self,
        feature: int,
        data: bytes | int | None = None,
        lba: int = 0,
    ) -> bytes | None:
        """Execute Vendor Unique Command (VUC).

        Args:
            feature: VUC feature.
            data: Data for write or data-size for read if any.
            lba: LBA register.

        Returns:
            Read data if any.

        """
        # Non-data VUCs use single sector write
        data = data or b"\0"

        command: ata_command.Command = (
            ata_command.Command.READ_SECTORS_NO_RETRY
            if isinstance(data, int)
            else ata_command.Command.WRITE_SECTORS_NO_RETRY
        )

        self._vuc_set_ap_key()

        data, _ = self.command(
            ata_command.CommandRegisters(
                feature=int(feature),
                lba=lba,
                command=command,
            ),
            data,
        )

        return data

    @property
    def mode(self) -> Mode:
        """Firmware mode.

        Raises:
            ValueError: Invalid mode.

        """
        identify_model_rom: str = "PS3111"

        # ROM mode doesn't support VUC system info
        # So first check for ROM mode with identify info
        identify: ata_identify.Identify = self.cmd_identify_device()

        try:
            id_firmware: s11_firmware.Version = s11_firmware.Version.from_string(
                identify.firmware,
            )
        except ValueError:
            pass
        else:
            if (
                id_firmware.firmware_type == s11_firmware.VersionType.ROM
                and identify.model == identify_model_rom
            ):
                return Mode.ROM

        # If not ROM mode, check with VUC system info
        sysinfo_firmware: s11_firmware.Version = self.vuc_system_info().firmware_version

        match sysinfo_firmware.firmware_type:
            case s11_firmware.VersionType.BURNER:
                return Mode.BURNER
            case s11_firmware.VersionType.NORMAL | s11_firmware.VersionType.RDT:
                return Mode.NORMAL
            case _:
                raise ValueError(
                    "Couldn't determine firmware mode from system info",
                    sysinfo_firmware,
                )

    @mode.setter
    def mode(self, value: Mode) -> None:
        reg_address: int = 0x04000044
        reg_normal: bytes = b"\x00"
        reg_rom: bytes = b"\x02"

        current_mode: Mode = self.mode

        match value:
            case x if x == current_mode:
                # Already in target mode
                return
            case Mode.ROM:
                # Switch to ROM from normal or burner
                self.vuc_write_register(reg_address, reg_rom)
                self.vuc_jump()
                self.vuc_write_register(reg_address, reg_normal)
            case Mode.NORMAL:
                if current_mode == Mode.ROM:
                    # Switch to normal from ROM
                    self.vuc_restart()
                else:
                    # Switch to normal from burner
                    self.vuc_write_register(reg_address, reg_normal)
                    self.vuc_jump()
            case x:
                # Switch to target mode unsupported (i.e. burner)
                raise ValueError("Can't set mode", x)

        if self.mode != value:
            raise ValueError("Failed to change mode", current_mode, value)

        # Re-unlock VUC
        self.vuc_unlock()

    def _vuc_unlock_engineering(self) -> None:
        # Check if engineering mode not needed
        system_info: s11_system_info.SystemInfo = self.vuc_system_info()
        if system_info.vuc_mode in (
            None,
            s11_system_info.VUCMode.ENGINEERING,
        ):
            return

        dlmc_data: bytes = bytes(s11_firmware.Header(engineering_mode=True))
        self.cmd_download_microcode_full(dlmc_data)

        # Verify engineering mode
        system_info = self.vuc_system_info()
        if system_info.vuc_mode != s11_system_info.VUCMode.ENGINEERING:
            raise ValueError(
                "VUC unlock engineering mode failed",
                system_info.vuc_mode,
            )

    def vuc_unlock(self) -> None:
        """Unlock VUC access.

        Raises:
            ValueError: Unlock failed.

        """
        # ROM mode has no lock
        if self.mode == Mode.ROM:
            return

        system_info: s11_system_info.SystemInfo = self.vuc_system_info()

        # Check if unlock not needed
        if system_info.vuc_mode in (
            None,
            s11_system_info.VUCMode.UNLOCKED,
            s11_system_info.VUCMode.NO_LOCK,
        ):
            return

        # Get key
        try:
            key: bytes = _VUC_UNLOCK_KEYS[system_info.vuc_key]
        except KeyError as e:
            raise ValueError("Invalid VUC key", system_info.vuc_key) from e

        # Reset state if needed
        self.vuc_lock()

        # Change to engineering mode
        self._vuc_unlock_engineering()

        # Unlock start
        self.vuc(VUCFeature.VUC_UNLOCK_START)

        # Read challenge
        read_data: bytes = self.vuc(
            VUCFeature.VUC_UNLOCK_READ,
            ata_command.SECTOR_SIZE,
        )

        # Encrypt challenge, two rounds
        seed: int = _vuc_unlock_derive_seed(key)
        write_data: bytes = s11_algorithm.cipher_crc16(read_data, seed)
        seed ^= _vuc_unlock_derive_seed(write_data)
        write_data = s11_algorithm.cipher_crc16(write_data, seed)

        # Write encrypted challenge
        self.vuc(VUCFeature.VUC_UNLOCK_WRITE, write_data)

        # Confirm unlocked
        system_info = self.vuc_system_info()
        if system_info.vuc_mode != s11_system_info.VUCMode.UNLOCKED:
            self.vuc_lock()  # Reset state
            raise ValueError("VUC unlock failed", system_info.vuc_mode)

    def vuc_lock(self) -> None:
        """Lock VUC access."""
        # ROM mode has no lock
        mode: Mode = self.mode
        if mode == Mode.ROM:
            return

        # Check if lock not needed
        if self.vuc_system_info().vuc_mode in (
            None,
            s11_system_info.VUCMode.LOCKED,
            s11_system_info.VUCMode.NO_LOCK,
        ):
            return

        # Lock
        self.vuc(VUCFeature.VUC_LOCK)

        # Verify locked to default mode
        # Sometimes (e.g. burner firmware or protected mode) default mode is engineering
        system_info: s11_system_info.SystemInfo = self.vuc_system_info()
        if system_info.vuc_mode not in (
            s11_system_info.VUCMode.LOCKED,
            s11_system_info.VUCMode.ENGINEERING,
        ):
            raise ValueError("VUC lock failed", system_info.vuc_mode)

    def vuc_jump(self) -> None:
        """VUC jump to code in RAM."""
        self.vuc(VUCFeature.JUMP)
        time.sleep(1)

    def vuc_restart(self) -> None:
        """Soft restart."""
        self.vuc(VUCFeature.RESTART)
        time.sleep(1)
        self.vuc_unlock()

    def vuc_system_info(self) -> s11_system_info.SystemInfo:
        """Read system information.

        Returns:
            System information.

        """
        data: bytes = self.vuc(
            VUCFeature.SYSTEM_INFO,
            s11_system_info.SystemInfo.SIZE,
        )

        return s11_system_info.SystemInfo.from_bytes(data)

    def vuc_read_info_block(self) -> s11_info_block.InfoBlock:
        """Read drive info block.

        Returns:
            Info block.

        """
        # This VUC supports a start offset based on the LBA low register:
        # 1: +512, 2: +1536, 3: +2048
        # Unimplemented here.

        data: bytes = self.vuc(
            VUCFeature.READ_INFO_BLOCK,
            s11_info_block.InfoBlock.SIZE,
        )
        return s11_info_block.InfoBlock.from_bytes(data)

    def vuc_write_info_block(
        self,
        info_block: s11_info_block.InfoBlock | bytes | bytearray,
    ) -> None:
        """Write drive info block.

        Args:
            info_block: Info block.

        """
        # This VUC supports a start offset based on the LBA low register:
        # 1: +512, 2: +1536, 3: +2048
        # Unimplemented here.

        info_block = bytes(info_block)
        self.vuc(VUCFeature.WRITE_INFO_BLOCK, info_block)

    def vuc_set_parameter(self, data: bytes) -> None:
        """Send parameter data for next VUC.

        Args:
            data: Parameter bytes to send.

        """
        self.vuc(VUCFeature.SET_PARAMETER, data)

    def vuc_read_register(self, address: int, size: int = 4) -> bytes:
        """Read data from memory.

        Args:
            address: Address.
            size: Size.

        Returns:
            Read data.

        """
        if size <= 0:
            raise ValueError("Invalid size", size)

        data: bytearray = bytearray()

        while (position := len(data)) < size:
            remaining: int = size - position
            register_address: int = address + position
            register_size: int = _register_size(remaining)
            lba: int = register_size << 8

            parameter_data: bytes = register_address.to_bytes(4, "little")
            self.vuc_set_parameter(parameter_data)

            read_size: int = len(parameter_data) + register_size
            read_data: bytes = self.vuc(VUCFeature.READ_REGISTER, read_size, lba)
            data += read_data[len(parameter_data) :]

        return bytes(data[:size])

    def vuc_write_register(self, address: int, data: bytes | bytearray) -> None:
        """Write data to memory.

        Args:
            address: Address.
            data: Data.

        """
        position: int = 0

        while remaining := len(data) - position:
            write_address: int = address + position
            write_size: int = _register_size(remaining)

            write_data: bytes = struct.pack(
                f"<L{write_size}s",
                write_address,
                data[position : position + write_size],
            )

            lba: int = write_size << 8

            self.vuc(
                VUCFeature.WRITE_REGISTER,
                write_data,
                lba,
            )

            position += write_size

    def vuc_read_sram(self, address: int, size: int) -> bytes:
        """Read data from SRAM.

        Args:
            address: Address.
            size: Size.

        Returns:
            Read data.

        """
        max_size: int = 32 * ata_command.SECTOR_SIZE

        data: bytearray = bytearray()

        while len(data) < size:
            position: int = len(data)
            remaining: int = size - position
            read_size: int = min(remaining, max_size)
            read_address: int = address + position

            self.vuc_set_parameter(read_address.to_bytes(4, "little"))
            read_data: bytes = self.vuc(VUCFeature.READ_SRAM, read_size)
            data += read_data

        return bytes(data)

    def _ce_address(
        self,
        ce_index: int,
        system_info: s11_system_info.SystemInfo | None = None,
    ) -> int:
        system_info = system_info or self.vuc_system_info()

        if not system_info.ce_count or not (0 <= ce_index < system_info.ce_count):
            raise ValueError("Invalid CE index", ce_index)

        addresses: list[int] = [
            x
            for x in range(system_info.ce_bitmap.bit_length())
            if (1 << x) & system_info.ce_bitmap
        ]

        if len(addresses) != system_info.ce_count:
            raise ValueError("Invalid CE bitmap", system_info.ce_bitmap)

        return addresses[ce_index]

    def vuc_flash_id(
        self,
        ce_index: int,
        system_info: s11_system_info.SystemInfo | None = None,
    ) -> FlashID:
        """Read flash ID for CE.

        Args:
            ce_index: CE index.
            system_info: System information.

        Returns:
            Flash ID.

        """
        ce_address: int = self._ce_address(ce_index, system_info)
        lba: int = ce_address << 16
        data: bytes = self.vuc(VUCFeature.FLASH_ID, FlashID.SIZE, lba)

        return FlashID.from_bytes(data)

    def vuc_flash_id_all(
        self,
        system_info: s11_system_info.SystemInfo | None = None,
    ) -> list[FlashID]:
        """Read flash ID for all CEs.

        Args:
            system_info: System information.

        Returns:
            Flash IDs.

        """
        system_info = system_info or self.vuc_system_info()

        if not system_info.ce_count:
            raise ValueError("No CE count")

        offsets: list[int] = [
            self._ce_address(x, system_info) * FlashID.SIZE
            for x in range(system_info.ce_count)
        ]
        data: bytes = self.vuc(
            VUCFeature.FLASH_ID_ALL,
            offsets[-1] + FlashID.SIZE,
        )

        return [FlashID.from_bytes(data[x : x + FlashID.SIZE]) for x in offsets]

    def _vuc_flash_set_parameter(
        self,
        ce_index: int,
        die: int,
        block: int,
        page: int,
        system_info: s11_system_info.SystemInfo | None,
    ) -> None:
        system_info = system_info or self.vuc_system_info()
        ce_address: int = self._ce_address(ce_index, system_info)

        if not system_info.dies_per_ce or die >= system_info.dies_per_ce:
            raise ValueError("Invalid die", die)

        if not system_info.blocks_per_die or block >= system_info.blocks_per_die:
            raise ValueError("Invalid block", block)

        if not system_info.pages_per_block or page >= system_info.pages_per_block:
            raise ValueError("Invalid page", page)

        die_block_address: int = die * (system_info.die_stride or 0)
        block_address: int = die_block_address + block

        parameter: bytes = struct.pack("<20xBxHH", ce_address, block_address, page)
        self.vuc_set_parameter(parameter)

    def vuc_read_flash(
        self,
        ce_index: int,
        die: int,
        block: int,
        page: int,
        pslc: bool,
        system_info: s11_system_info.SystemInfo | None = None,
    ) -> tuple[bytes, int]:
        """Read raw flash page.

        Args:
            ce_index: CE index.
            die: Die index.
            block: Block index.
            page: Page index.
            pslc: Pseudo-SLC mode.
            system_info: System information if any.

        Returns:
            (data, OOB metadata magic).

        """
        system_info = system_info or self.vuc_system_info()
        self._vuc_flash_set_parameter(ce_index, die, block, page, system_info)

        if not system_info.sectors_per_page:
            raise ValueError("No sectors per page")

        data_size: int = system_info.sectors_per_page * ata_command.SECTOR_SIZE
        read_size: int = data_size + ata_command.SECTOR_SIZE

        # Bits 23:16: Parameter address format
        # Bit 15: Pseudo-SLC
        # Bit 14: Don't verify ECC
        # Bit 13: Metadata/OOB only
        # Bit 11: Read only single 4kb ECC frame
        # Bit 7:0: Read full page, otherwise single-sector
        lba: int = (int(True) << 16) | (int(pslc) << 15) | int(True)

        read_data: bytes = self.vuc(VUCFeature.READ_FLASH, read_size, lba)

        data: bytes = read_data[:data_size]
        metadata: bytes = read_data[-ata_command.SECTOR_SIZE :]
        magic: int = int.from_bytes(metadata[:4], "little")

        return data, magic

    def vuc_write_flash(
        self,
        ce_index: int,
        die: int,
        block: int,
        page: int,
        pslc: bool,
        data: bytes,
        system_info: s11_system_info.SystemInfo | None = None,
    ) -> None:
        """Write raw flash page.

        Args:
            ce_index: CE index.
            die: Die index.
            block: Block index.
            page: Page index.
            pslc: Pseudo-SLC mode.
            data: Page data.
            system_info: System information if any.

        """
        self._vuc_flash_set_parameter(ce_index, die, block, page, system_info)

        # Bits 23:16: Parameter address format
        # Bit 15: Pseudo-SLC
        lba: int = (int(True) << 16) | (int(pslc) << 15)

        self.vuc(VUCFeature.WRITE_FLASH, data, lba)

    def vuc_erase_flash(
        self,
        ce_index: int,
        die: int,
        block: int,
        pslc: bool,
        system_info: s11_system_info.SystemInfo | None = None,
    ) -> None:
        """Erase raw flash block.

        Args:
            ce_index: CE index.
            die: Die index.
            block: Block index.
            pslc: Pseudo-SLC mode.
            system_info: System information if any.

        """
        self._vuc_flash_set_parameter(ce_index, die, block, 0, system_info)

        # Bits 23:16: Parameter address format
        # Bit 15: Pseudo-SLC
        lba: int = (int(True) << 16) | (int(pslc) << 15)

        self.vuc(VUCFeature.ERASE_FLASH, lba=lba)

    def vuc_send_seed(self, seed: bytes | s11_firmware.Seed) -> None:
        """Send firmware metadata.

        Args:
            seed: Firmware seed.

        """
        self.vuc(VUCFeature.SEND_SEED, bytes(seed))

    def vuc_verify_flash(
        self,
    ) -> tuple[s11_flash.FirmwareHeader, tuple[bytes, ...]]:
        """Read back firmware from flash.

        Returns:
            (Header, Sections).

        """
        header_data: bytes = self.vuc(
            VUCFeature.VERIFY_FLASH,
            s11_flash.FirmwareHeader.SIZE,
        )
        header: s11_flash.FirmwareHeader = s11_flash.FirmwareHeader.from_bytes(
            header_data,
        )

        sections: list[bytes] = []

        for section_info in (x for x in header.sections if x):
            section: bytearray = bytearray()

            while len(section) < section_info.size:
                read_size: int = min(
                    section_info.size - len(section),
                    self._CMD_MAX_SIZE,
                )
                lba: int = 1 << 16
                read_data: bytes = self.vuc(
                    VUCFeature.VERIFY_FLASH,
                    read_size,
                    lba=lba,
                )
                section += read_data

            sections.append(bytes(section))

        return header, tuple(sections)

    def vuc_program_pram(
        self,
        address: int,
        data: bytes,
        encrypted: bool = False,
    ) -> None:
        """Write code to instruction RAM.

        Args:
            address: Address.
            data: Code data.
            encrypted: Data encrypted.

        Raises:
            ValueError: CRC verification failed.

        """
        crc_result_struct: struct.Struct = struct.Struct("<8xL")
        crc_result_ok: int = 0x55AA55AA

        # Write code
        for position in range(0, len(data), self._CMD_MAX_SIZE):
            write_address: int = address + position
            write_size: int = min(len(data) - position, self._CMD_MAX_SIZE)
            write_data: bytes = data[position : position + write_size]

            parameter: bytes = struct.pack("<LL", write_address, write_size)
            self.vuc_set_parameter(parameter)

            lba: int = int(encrypted) << 8
            self.vuc(VUCFeature.PROGRAM_PRAM, write_data, lba)

        # Check CRC
        crc_parameter: bytes = struct.pack("<LL", address, len(data))
        self.vuc_set_parameter(crc_parameter)
        crc_result_data: bytes = self.vuc(
            VUCFeature.CHECK_CRC,
            crc_result_struct.size,
        )

        crc_result: int = crc_result_struct.unpack_from(crc_result_data)[0]

        if crc_result != crc_result_ok:
            raise ValueError("CRC check failed", crc_result)

    def vuc_program_pram_icode(self, data: bytes) -> None:
        """Write code to SRAM.

        Args:
            data: Code data.

        Raises:
            ValueError: Write failed.

        """
        for position in range(0, len(data), self._CMD_MAX_SIZE):
            write_data: bytes = data[position : position + self._CMD_MAX_SIZE]
            final: bool = len(data) - position <= self._CMD_MAX_SIZE
            chunk_index: int = position // self._CMD_MAX_SIZE

            # Write code
            write_lba: int = (int(final) << 8) | (chunk_index << 16)
            self.vuc(VUCFeature.PROGRAM_PRAM_ICODE, write_data, write_lba)

            # Read back code
            read_lba: int = chunk_index << 16
            read_data: bytes = self.vuc(
                VUCFeature.VERIFY_PRAM_ICODE,
                len(write_data),
                read_lba,
            )

            if read_data != write_data:
                raise ValueError("Verify code failed", chunk_index)

    def vuc_block_map(
        self,
        channel: int,
        system_info: s11_system_info.SystemInfo | None = None,
    ) -> tuple[tuple[tuple[BlockType, int] | None, ...], ...]:
        """Read map of flash blocks.

        Args:
            channel: Flash channel index.
            system_info: System information.

        Returns:
            Map of flash blocks.

        """
        chunk_size: int = 4_096

        system_info = system_info or self.vuc_system_info()

        if not system_info.dies_per_ce:
            raise ValueError("No dies per CE")

        if not system_info.blocks_per_die:
            raise ValueError("No blocks per die")

        if not (0 <= channel < system_info.channel_count):
            raise ValueError("Invalid channel", channel)

        die_stride: int = system_info.die_stride or 0

        entry_count: int = (
            system_info.dies_per_ce - 1
        ) * die_stride + system_info.blocks_per_die
        entries_struct: struct.Struct = struct.Struct(f"<{entry_count}L")

        read_size: int = -(entries_struct.size // -chunk_size) * chunk_size
        lba: int = channel << 8
        data: bytes = self.vuc(VUCFeature.BLOCK_MAP, read_size, lba)

        values: tuple[int, ...] = entries_struct.unpack_from(data)
        block_map: list[tuple[tuple[BlockType, int] | None, ...]] = []

        for die in range(system_info.dies_per_ce):
            die_block_start: int = die * die_stride
            die_values: tuple[int, ...] = values[
                die_block_start : die_block_start + system_info.blocks_per_die
            ]
            block_map.append(
                tuple((BlockType(x & 0xFF), x >> 8) if x else None for x in die_values),
            )

        return tuple(block_map)
