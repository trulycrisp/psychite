"""Phison S11 info block."""

import dataclasses
import enum
import struct
from typing import ClassVar, Self

from phison_s11 import data as s11_data
from phison_s11.ata import identify


class Brand(enum.IntEnum):
    """OEM brand identifier.

    Attributes:
        PHISON: Phison.
        ADVANTECH: Advantech.
        APACER: Apacer.
        ASUS: ASUS.
        CORSAIR: Corsair.
        HAGIWARA: Hagiwara.
        HP: HP.
        IMATION: Imation.
        JDS: JDS.
        JUSTRAM: JustRAM.
        KINGSTON: Kingston.
        PDP: PDP.
        KIOXIA: Kioxia.
        UNIGEN_USA: Unigen USA.
        ELBIT: Elbit.
        LEGACY: Legacy.
        NETLIST: Netlist.
        NETPOSA: Netposa.
        ACER: Acer.
        PROMISE: Promise.
        GLYN: Glyn.
        VIKING: Viking.
        SMARTM: SmartM.
        THREEGNET: 3GNet.
        RAMAXEL: Ramaxel.
        NORMAL: Normal.
        SONY: Sony.
        SWISSBIT: Swissbit.
        KIOXIA_TEC: Kioxia TEC.
        STEC_HGST: STEC/HGST.
        DELL_KINGSTON: Dell/Kingston.
        NEC_TACHIBANA: NEC/Tachibana.
        AVANT: Avant Technology.
        TACHIBANA_PANA_STRBD: Tachibana Panasonic set-top recorder.
        MHGST: (Mobile?) HGST.
        GALAXY: Galax (formerly Galaxy Microsystems).
        LITEON: LITEON.
        UNKNOWN1: Unknown, minor variation to SMART behaviour.
        UNKNOWN2: Unknown, requires signed firmware updates.
        UNKNOWN3: Unknown, variant of "Normal".
        UDINFO: UDinfo.
        IMICRO: iMicro.
        GLOWAY: Gloway.
        DELKIN: Delkin.

    """

    PHISON = 0
    ADVANTECH = 1
    APACER = 2
    ASUS = 3
    CORSAIR = 4
    HAGIWARA = 5
    HP = 6
    IMATION = 7
    JDS = 8
    JUSTRAM = 9
    KINGSTON = 10
    PDP = 11
    KIOXIA = 12
    UNIGEN_USA = 13
    ELBIT = 14
    LEGACY = 15
    NETLIST = 16
    NETPOSA = 17
    ACER = 18
    PROMISE = 19
    GLYN = 20
    VIKING = 21
    SMARTM = 22
    THREEGNET = 23
    RAMAXEL = 24
    NORMAL = 25
    SONY = 26
    SWISSBIT = 27
    KIOXIA_TEC = 28
    STEC_HGST = 29
    DELL_KINGSTON = 30
    NEC_TACHIBANA = 31
    AVANT = 32
    TACHIBANA_PANA_STRBD = 33
    MHGST = 34
    GALAXY = 35
    LITEON = 36
    UNKNOWN1 = 40
    UNKNOWN2 = 55
    UNKNOWN3 = 78
    UDINFO = 82
    IMICRO = 97
    GLOWAY = 98
    DELKIN = 100


class Interleave(enum.IntEnum):
    """Interleave mode.

    Attributes:
        DISABLE: Disable interleave.
        STRIDE_2: Interleave stride 2.
        STRIDE_4: Interleave stride 4.
        STRIDE_8: Interleave stride 8.

    """

    DISABLE = 1
    STRIDE_2 = 2
    STRIDE_4 = 3
    STRIDE_8 = 4


class TemperatureSensor(enum.IntEnum):
    """Temperature sensor in info block.

    Attributes:
        I2C: Use I2C sensor.
        FLASH: Use sensor in flash chips.
        DISABLED: Disable sensor (use hardcoded 33 celsius).
        FIXED: Use fixed value for temperature.

    """

    I2C = 1
    FLASH = 2
    DISABLED = 3
    FIXED = 4


@dataclasses.dataclass
class InfoBlock:
    """Info block.

    Attributes:
        unknown1: Unknown data.
        serial: Serial number.
        model: Model name.
        firmware_enable: Enable following field firmware.
        firmware: Firmware version string.
        brand: OEM brand identifier.
        wwn_enable: Enable WWN (field wwn), None behaves as True.
        ce_limit: Max number of chip enables to use.
        wwn: Word Wide Name.
        form_factor: Form factor.
        unknown2: Unknown data.
        addressable_sectors: Total addressable sectors, None uses internal default.
        interleave: Flash interleave type, None uses internal default.
        unknown3: Unknown data.
        flash_interface: Flash interface type, None uses internal default.
        unknown4: Unknown data.
        temperature_sensor: Temperature sensor type, None uses internal default.
        devslp_enable: Enable DevSlp, None behaves as False.
        ncq_enable: Enable Native Command Queuing, None behaves as True.
        lba48_enable: Enable 48-bit Logical Block Addressing, None behaves as True.
        dma_modes_enable: Use the following mwdma_*/udma_* fields, None behaves as True.
        mwdma_supported_modes: Supported Multi-Word DMA modes bitmask, format of ATA
            identify word 63 bits 7:0.
        mwdma_initial_mode: Initial active Multi-Word DMA mode, mode is highest set bit.
        udma_supported_modes: Supported UDMA modes bitmask, format of ATA identify word
            88 bits 7:0.
        udma_initial_mode: Initial active UDMA mode, mode is highest set bit.
        force_pslc: Force all flash access to pseudo-SLC, None behaves as False.
        write_cache_enable: Enable write cache, None behaves as True.
        pe_cycle_limit: Number of program/erase cycles a flash block can endure, None
            uses internal default.
        unknown5: Unknown data.
        pslc_cache_size: Pseudo-SLC cache size in units of 4096 bytes, requires
            pslc_cache_size_enable.
        identify_vendor_specific: ATA identify words 129-159 (vendor-specific).
        identify_vendor_specific_enable: Enable field identify_vendor_specific, None
            behaves as True.
        pslc_cache_size_enable: Enable field pslc_cache_size.
        sata_ssc_enable: Enable Spread Spectrum Clocking, None uses hardware default.
        hipm_enable: Enable Host Initiated Power Management, None behaves as False.
        dipm_enable: Enable Device Initiated Power Management, None behaves as True.
        device_apst_enable: Enable device Automatic Partial to Slumber transitions,
            None behaves as False.
        smart_threshold_direction: Bitmask for threshold comparison direction of SMART
            attributes. Bit N is attribute N, 0 is higher better and 1 lower better.
        dipm_threshold: Idle ticks before Device Initiated Power Management request,
            None uses default 50.
        idle_threshold: Idle ticks before various idle background tasks performed,
            None uses default 1000.
        idle_enable: Enable various idle tasks and power management.
        flush_cache_disable: Disable ATA FLUSH CACHE command, None behaves as False.
        unknown6: Unknown data.
        gc_pressure_enable: Enable FTL GC pressure configuration.
        unknown7: Unknown data.
        unknown8: Unknown data.
        unknown9: Unknown data.
        dco_enable: Enable Device Configuration Overlay functionality such as DCO SET
            command, None behaves as True.
        hpa_enable: Enable Host Protected Area functionality (e.g. SET MAX ADDRESS
            command), None behaves as True.
        amac_enable: Enable Accessible Max Address Configuration functionality (e.g.
            ACCESSIBLE MAX ADDRESS CONFIGURATION command), None behaves as False.
        pe_cycle_limit_pslc: Number of program/erase cycles a flash block can endure
            in pseudo-SLC mode, None uses internal default.
        sanitize_enable: Enable SANITIZE DEVICE command, None behaves as False.
        write_uncorrectable_ext_enable: Enable WRITE UNCORRECTABLE EXT command, None
            behaves as True.
        zero_ext_enable: Enable ZERO EXT command, None behaves as True.
        unknown10: Unknown data.
        flush_cache_sync: FLUSH CACHE command is synchronous, None behaves as False.
        unknown11: Unknown data.
        apst_timeout: Ticks in milliseconds to wait for APST Partial to Slumber
            transition before cancelled with a forced wake, None uses internal default.
        unknown12: Unknown data.
        smart_log_dfh: String returned by SMART log 0xDF.
        max_pe_cycles_pslc_superblock: Max number of pseudo-SLC program erase cycles
            averaged over every superblock, when reached FTL switches to native mode
            (e.g. TLC). None uses internal default.
        security_enable: Enable the security feature set (e.g. security erase), None
            behaves as True.
        dlmc_enable: Enable the DOWNLOAD MICROCODE command, None behaves as True.
        trim_enable: Enable TRIM functionality, None behaves as True.
        dlmc_block_trailing: DOWNLOAD MICROCODE blocks extra trailing data by raising an
            Error, None behaves as True.
        unknown13: Unknown data.
        wear_level_margin: Maximum P/E count difference between superblocks before
            wear-leveling intervention, None uses internal default.
        unknown14: Unknown data.
        wear_level_pslc_interval: Poll interval used for pseudo-SLC wear leveling,
            higher values make it run less often. None uses internal default.
        unknown15: Unknown data.
        selftest_enable: Enable SMART self-test functionality, None behaves as True.
        protected_allow_write: Allow data write when firmware is in protect mode
            (SATAFIRM), None behaves as True.
        hw_security_erase1_mode: Mode for unknown secure erase feature triggered by
            hardware GPIO, channel 1 Values are 1 to 4, None disables.
        selftest_extended_untimed: Disable time limit for extended self-test, None
            behave as False.
        unknown16: Unknown data.
        protected_info_enable: Enable fields firmware_protected and model_protected.
        firmware_protected: Protected mode firmware version string.
        model_protected: Protected mode drive model string.
        unknown17: Unknown data.
        selftest_short_time_limit: Time limit in minutes for short self-test, None
            uses internal default.
        selftest_conveyance_time_limit: Time limit in minutes for conveyance self-test,
            None uses internal default.
        selftest_extended_time_limit: Time limit in minutes for extended self-test,
            None uses internal default.
        offline_data_collection_time_limit: Time limit in seconds for SMART offline
            data collection, None uses internal default.
        security_erase_always_enhanced: Force all security erases to be enhanced, None
            behaves as True.
        hw_security_erase1_polarity: Hardware polarity for hw_security_erase1_mode,
            0/1=active-high >1=active-low, channel 1.
        unknown18: Unknown data.
        hw_security_erase2_mode: Similar to hw_security_erase1_mode, but for alternate
            hardware trigger (channel 2). None disables.
        hw_security_erase2_polarity: Similar to hw_security_erase1_polarity, but for
            channel 2.
        brand_17h_cmd_test: Enables an unknown manufacturing test mode for brand 0x17,
            verifies ATA command sequence and DMA write pattern from host.
        unknown19: Unknown data.
        ftl_force_reserve_blocks: Force the FTL to allocate reserved blocks beyond
            strictly needed for capacity, otherwise chooses internally.
        unknown20: Unknown data.
        vuc_6fh_secure_erase_enable: Enables VUC (ATA cmd 0x6F) that performs a variant
            of secure erase.
        unknown21: Unknown data.

    """

    _MAGIC: ClassVar[bytes] = b"PhIsOn"
    _FIRMWARE_SIZE: ClassVar[int] = 8
    _SERIAL_SIZE: ClassVar[int] = 20
    _MODEL_SIZE: ClassVar[int] = 40
    _MODEL_PROTECTED_SIZE: ClassVar[int] = 20
    _STRUCT: ClassVar[struct.Struct] = struct.Struct(
        f"<{len(_MAGIC)}s"
        "12s"
        f"{_SERIAL_SIZE}s"
        f"{_MODEL_SIZE}s"
        "B"
        f"{_FIRMWARE_SIZE}s"
        "3B"
        f"{identify.WWN.SIZE}s"
        "B"
        "1s"
        "L"
        "B"
        "2s"
        "B"
        "1s"
        "11B"
        "L"
        "12s"
        "L"
        "62s"
        "B"
        "?"
        "4B"
        "3L"
        "2B"
        "5s"
        "?"
        "8s"
        "1s"
        "16s"
        "3B"
        "L"
        "3B"
        "1s"
        "B"
        "2s"
        "B"
        "2s"
        "20s"
        "H"
        "4B"
        "2s"
        "H"
        "3s"
        "B"
        "48s"
        "4B"
        "1s"
        "B"
        f"{_FIRMWARE_SIZE}s"
        f"{_MODEL_PROTECTED_SIZE}s"
        "6s"
        "2B"
        "2H"
        "2B"
        "2s"
        "2B"
        "?"
        "5s"
        "?"
        "1s"
        "?"
        "99s",
    )
    _OPTIONAL_BOOL_MAP: ClassVar[dict[int, bool | None]] = {0: None, 1: True, 2: False}
    SIZE: ClassVar[int] = _STRUCT.size

    unknown1: bytes
    serial: str
    model: str
    firmware_enable: bool
    firmware: str | None
    brand: Brand
    wwn_enable: bool | None
    ce_limit: int | None
    wwn: identify.WWN | None
    form_factor: identify.FormFactor | None
    unknown2: bytes
    addressable_sectors: int | None
    interleave: Interleave | None
    unknown3: bytes
    flash_interface: s11_data.FlashInterface | None
    unknown4: bytes
    temperature_sensor: TemperatureSensor | None
    devslp_enable: bool | None
    ncq_enable: bool | None
    lba48_enable: bool | None
    dma_modes_enable: bool | None
    mwdma_supported_modes: int
    mwdma_initial_mode: int
    udma_supported_modes: int
    udma_initial_mode: int
    force_pslc: bool | None
    write_cache_enable: bool | None
    pe_cycle_limit: int | None
    unknown5: bytes
    pslc_cache_size: int
    identify_vendor_specific: bytes
    identify_vendor_specific_enable: bool | None
    pslc_cache_size_enable: bool
    sata_ssc_enable: bool | None
    hipm_enable: bool | None
    dipm_enable: bool | None
    device_apst_enable: bool | None
    smart_threshold_direction: int
    dipm_threshold: int | None
    idle_threshold: int | None
    idle_enable: bool | None
    flush_cache_disable: bool | None
    unknown6: bytes
    gc_pressure_enable: bool
    unknown7: bytes
    unknown8: bytes
    unknown9: bytes
    dco_enable: bool | None
    hpa_enable: bool | None
    amac_enable: bool | None
    pe_cycle_limit_pslc: int | None
    sanitize_enable: bool | None
    write_uncorrectable_ext_enable: bool | None
    zero_ext_enable: bool | None
    unknown10: bytes
    flush_cache_sync: bool | None
    unknown11: bytes
    apst_timeout: int | None
    unknown12: bytes
    smart_log_dfh: str
    max_pe_cycles_pslc_superblock: int | None
    security_enable: bool | None
    dlmc_enable: bool | None
    trim_enable: bool | None
    dlmc_block_trailing: bool | None
    unknown13: bytes
    wear_level_margin: int | None
    unknown14: bytes
    wear_level_pslc_interval: int | None
    unknown15: bytes
    selftest_enable: bool | None
    protected_allow_write: bool | None
    hw_security_erase1_mode: int | None
    selftest_extended_untimed: bool | None
    unknown16: bytes
    protected_info_enable: bool
    firmware_protected: str | None
    model_protected: str | None
    unknown17: bytes
    selftest_short_time_limit: int | None
    selftest_conveyance_time_limit: int | None
    selftest_extended_time_limit: int | None
    offline_data_collection_time_limit: int | None
    security_erase_always_enhanced: bool | None
    hw_security_erase1_polarity: int
    unknown18: bytes
    hw_security_erase2_mode: int | None
    hw_security_erase2_polarity: int
    brand_17h_cmd_test: bool
    unknown19: bytes
    ftl_force_reserve_blocks: bool
    unknown20: bytes
    vuc_6fh_secure_erase_enable: bool
    unknown21: bytes

    @classmethod
    def _optional_bool_pack(cls, value: bool | None) -> int:
        return next(k for k, v in cls._OPTIONAL_BOOL_MAP.items() if v == value)

    @classmethod
    def _optional_bool_unpack(cls, value: int) -> bool | None:
        return cls._OPTIONAL_BOOL_MAP[value]

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Unpack info block from bytes.

        Args:
            data: Bytes.

        Returns:
            Info block.

        """
        magic: bytes
        unknown1: bytes
        serial_raw: bytes
        model_raw: bytes
        firmware_enable_raw: int
        firmware_raw: bytes
        brand_raw: int
        wwn_enable_raw: int
        ce_limit_raw: int
        wwn_raw: bytes
        form_factor_raw: int
        unknown2: bytes
        addressable_sectors_raw: int
        interleave_raw: int
        unknown3: bytes
        flash_interface_raw: int
        unknown4: bytes
        temperature_sensor_raw: int
        devslp_enable_raw: int
        ncq_enable_raw: int
        lba48_enable_raw: int
        dma_modes_enable_raw: int
        mwdma_supported_modes: int
        mwdma_initial_mode: int
        udma_supported_modes: int
        udma_initial_mode: int
        force_pslc_raw: int
        write_cache_enable_raw: int
        pe_cycle_limit_raw: int
        unknown5: bytes
        pslc_cache_size: int
        identify_vendor_specific: bytes
        identify_vendor_specific_enable_raw: int
        pslc_cache_size_enable: bool
        sata_ssc_enable_raw: int
        hipm_enable_raw: int
        dipm_enable_raw: int
        device_apst_enable_raw: int
        smart_threshold_direction: int
        dipm_threshold_raw: int
        idle_threshold_raw: int
        idle_enable_raw: int
        flush_cache_disable_raw: int
        unknown6: bytes
        gc_pressure_enable: bool
        unknown7: bytes
        unknown8: bytes
        unknown9: bytes
        dco_enable_raw: int
        hpa_enable_raw: int
        amac_enable_raw: int
        pe_cycle_limit_pslc_raw: int
        sanitize_enable_raw: int
        write_uncorrectable_ext_enable_raw: int
        zero_ext_enable_raw: int
        unknown10: bytes
        flush_cache_sync_raw: int
        unknown11: bytes
        apst_timeout_raw: int
        unknown12: bytes
        smart_log_dfh_raw: bytes
        max_pe_cycles_pslc_superblock_raw: int
        security_enable_raw: int
        dlmc_enable_raw: int
        trim_enable_raw: int
        dlmc_block_trailing_raw: int
        unknown13: bytes
        wear_level_margin_raw: int
        unknown14: bytes
        wear_level_pslc_interval_raw: int
        unknown15: bytes
        selftest_enable_raw: int
        protected_allow_write_raw: int
        hw_security_erase1_mode_raw: int
        selftest_extended_untimed_raw: int
        unknown16: bytes
        protected_info_enable_raw: int
        firmware_protected_raw: bytes
        model_protected_raw: bytes
        unknown17: bytes
        selftest_short_time_limit_raw: int
        selftest_conveyance_time_limit_raw: int
        selftest_extended_time_limit_raw: int
        offline_data_collection_time_limit_raw: int
        security_erase_always_enhanced_raw: int
        hw_security_erase1_polarity: int
        unknown18: bytes
        hw_security_erase2_mode_raw: int
        hw_security_erase2_polarity: int
        brand_17h_cmd_test: bool
        unknown19: bytes
        ftl_force_reserve_blocks: bool
        unknown20: bytes
        vuc_6fh_secure_erase_enable: bool
        unknown21: bytes
        (
            magic,
            unknown1,
            serial_raw,
            model_raw,
            firmware_enable_raw,
            firmware_raw,
            brand_raw,
            wwn_enable_raw,
            ce_limit_raw,
            wwn_raw,
            form_factor_raw,
            unknown2,
            addressable_sectors_raw,
            interleave_raw,
            unknown3,
            flash_interface_raw,
            unknown4,
            temperature_sensor_raw,
            devslp_enable_raw,
            ncq_enable_raw,
            lba48_enable_raw,
            dma_modes_enable_raw,
            mwdma_supported_modes,
            mwdma_initial_mode,
            udma_supported_modes,
            udma_initial_mode,
            force_pslc_raw,
            write_cache_enable_raw,
            pe_cycle_limit_raw,
            unknown5,
            pslc_cache_size,
            identify_vendor_specific,
            identify_vendor_specific_enable_raw,
            pslc_cache_size_enable,
            sata_ssc_enable_raw,
            hipm_enable_raw,
            dipm_enable_raw,
            device_apst_enable_raw,
            smart_threshold_direction,
            dipm_threshold_raw,
            idle_threshold_raw,
            idle_enable_raw,
            flush_cache_disable_raw,
            unknown6,
            gc_pressure_enable,
            unknown7,
            unknown8,
            unknown9,
            dco_enable_raw,
            hpa_enable_raw,
            amac_enable_raw,
            pe_cycle_limit_pslc_raw,
            sanitize_enable_raw,
            write_uncorrectable_ext_enable_raw,
            zero_ext_enable_raw,
            unknown10,
            flush_cache_sync_raw,
            unknown11,
            apst_timeout_raw,
            unknown12,
            smart_log_dfh_raw,
            max_pe_cycles_pslc_superblock_raw,
            security_enable_raw,
            dlmc_enable_raw,
            trim_enable_raw,
            dlmc_block_trailing_raw,
            unknown13,
            wear_level_margin_raw,
            unknown14,
            wear_level_pslc_interval_raw,
            unknown15,
            selftest_enable_raw,
            protected_allow_write_raw,
            hw_security_erase1_mode_raw,
            selftest_extended_untimed_raw,
            unknown16,
            protected_info_enable_raw,
            firmware_protected_raw,
            model_protected_raw,
            unknown17,
            selftest_short_time_limit_raw,
            selftest_conveyance_time_limit_raw,
            selftest_extended_time_limit_raw,
            offline_data_collection_time_limit_raw,
            security_erase_always_enhanced_raw,
            hw_security_erase1_polarity,
            unknown18,
            hw_security_erase2_mode_raw,
            hw_security_erase2_polarity,
            brand_17h_cmd_test,
            unknown19,
            ftl_force_reserve_blocks,
            unknown20,
            vuc_6fh_secure_erase_enable,
            unknown21,
        ) = cls._STRUCT.unpack(data)

        if magic != cls._MAGIC:
            raise ValueError("Invalid magic", magic)

        serial: str
        model: str
        serial, model = (identify.decode_string(x) for x in (serial_raw, model_raw))

        firmware_enable: bool = s11_data.bool_unpack(firmware_enable_raw)
        firmware: str | None = (
            identify.decode_string(firmware_raw) if any(firmware_raw) else None
        )

        brand: Brand = Brand(brand_raw)
        wwn_enable: bool | None = cls._optional_bool_unpack(wwn_enable_raw)
        ce_limit: int | None = ce_limit_raw or None

        wwn: identify.WWN | None = identify.WWN.parse(wwn_raw) if any(wwn_raw) else None

        form_factor: identify.FormFactor | None = identify.FormFactor.parse(
            form_factor_raw,
        )

        addressable_sectors: int | None = addressable_sectors_raw or None
        interleave: Interleave | None = (
            Interleave(interleave_raw) if interleave_raw else None
        )
        flash_interface: s11_data.FlashInterface | None = (
            s11_data.FlashInterface(flash_interface_raw)
            if flash_interface_raw
            else None
        )

        temperature_sensor: TemperatureSensor | None = (
            TemperatureSensor(temperature_sensor_raw)
            if temperature_sensor_raw
            else None
        )

        devslp_enable: bool | None
        ncq_enable: bool | None
        lba48_enable: bool | None
        dma_modes_enable: bool | None
        force_pslc: bool | None
        write_cache_enable: bool | None
        (
            devslp_enable,
            ncq_enable,
            lba48_enable,
            dma_modes_enable,
            force_pslc,
            write_cache_enable,
        ) = (
            cls._optional_bool_unpack(x)
            for x in (
                devslp_enable_raw,
                ncq_enable_raw,
                lba48_enable_raw,
                dma_modes_enable_raw,
                force_pslc_raw,
                write_cache_enable_raw,
            )
        )

        pe_cycle_limit: int | None = pe_cycle_limit_raw or None

        identify_vendor_specific_enable: bool | None = cls._optional_bool_unpack(
            identify_vendor_specific_enable_raw,
        )

        sata_ssc_enable: bool | None = cls._optional_bool_unpack(
            sata_ssc_enable_raw,
        )

        hipm_enable: bool | None
        dipm_enable: bool | None
        device_apst_enable: bool | None
        hipm_enable, dipm_enable, device_apst_enable = (
            cls._optional_bool_unpack(x)
            for x in (hipm_enable_raw, dipm_enable_raw, device_apst_enable_raw)
        )

        dipm_threshold: int | None = dipm_threshold_raw or None
        idle_threshold: int | None = idle_threshold_raw or None

        idle_enable: bool | None
        flush_cache_disable: bool | None
        dco_enable: bool | None
        hpa_enable: bool | None
        amac_enable: bool | None
        (
            idle_enable,
            flush_cache_disable,
            dco_enable,
            hpa_enable,
            amac_enable,
        ) = (
            cls._optional_bool_unpack(x)
            for x in (
                idle_enable_raw,
                flush_cache_disable_raw,
                dco_enable_raw,
                hpa_enable_raw,
                amac_enable_raw,
            )
        )

        pe_cycle_limit_pslc: int | None = pe_cycle_limit_pslc_raw or None

        sanitize_enable: bool | None
        write_uncorrectable_ext_enable: bool | None
        zero_ext_enable: bool | None
        flush_cache_sync: bool | None
        (
            sanitize_enable,
            write_uncorrectable_ext_enable,
            zero_ext_enable,
            flush_cache_sync,
        ) = (
            cls._optional_bool_unpack(x)
            for x in (
                sanitize_enable_raw,
                write_uncorrectable_ext_enable_raw,
                zero_ext_enable_raw,
                flush_cache_sync_raw,
            )
        )

        apst_timeout: int | None = apst_timeout_raw or None
        smart_log_dfh: str = smart_log_dfh_raw.decode()
        max_pe_cycles_pslc_superblock: int | None = (
            max_pe_cycles_pslc_superblock_raw or None
        )

        security_enable: bool | None
        dlmc_enable: bool | None
        trim_enable: bool | None
        dlmc_block_trailing: bool | None
        (
            security_enable,
            dlmc_enable,
            trim_enable,
            dlmc_block_trailing,
        ) = (
            cls._optional_bool_unpack(x)
            for x in (
                security_enable_raw,
                dlmc_enable_raw,
                trim_enable_raw,
                dlmc_block_trailing_raw,
            )
        )

        wear_level_margin: int | None = wear_level_margin_raw or None
        wear_level_pslc_interval: int | None = wear_level_pslc_interval_raw or None

        selftest_enable: bool | None
        protected_allow_write: bool | None
        (
            selftest_enable,
            protected_allow_write,
        ) = (
            cls._optional_bool_unpack(x)
            for x in (
                selftest_enable_raw,
                protected_allow_write_raw,
            )
        )

        hw_security_erase1_mode: int | None = hw_security_erase1_mode_raw or None

        selftest_extended_untimed: bool | None = cls._optional_bool_unpack(
            selftest_extended_untimed_raw,
        )

        protected_info_enable: bool = s11_data.bool_unpack(protected_info_enable_raw)

        firmware_protected: str | None
        model_protected: str | None
        firmware_protected, model_protected = (
            (identify.decode_string(x) if any(x) else None)
            for x in (firmware_protected_raw, model_protected_raw)
        )

        selftest_short_time_limit: int | None = selftest_short_time_limit_raw or None

        selftest_conveyance_time_limit: int | None = (
            selftest_conveyance_time_limit_raw or None
        )

        selftest_extended_time_limit: int | None = (
            selftest_extended_time_limit_raw or None
        )

        offline_data_collection_time_limit: int | None = (
            offline_data_collection_time_limit_raw or None
        )

        security_erase_always_enhanced: bool | None = cls._optional_bool_unpack(
            security_erase_always_enhanced_raw,
        )

        hw_security_erase2_mode: int | None = hw_security_erase2_mode_raw or None

        return cls(
            unknown1=unknown1,
            serial=serial,
            model=model,
            firmware_enable=firmware_enable,
            firmware=firmware,
            brand=brand,
            wwn_enable=wwn_enable,
            ce_limit=ce_limit,
            wwn=wwn,
            form_factor=form_factor,
            unknown2=unknown2,
            addressable_sectors=addressable_sectors,
            interleave=interleave,
            unknown3=unknown3,
            flash_interface=flash_interface,
            unknown4=unknown4,
            temperature_sensor=temperature_sensor,
            devslp_enable=devslp_enable,
            ncq_enable=ncq_enable,
            lba48_enable=lba48_enable,
            dma_modes_enable=dma_modes_enable,
            mwdma_supported_modes=mwdma_supported_modes,
            mwdma_initial_mode=mwdma_initial_mode,
            udma_supported_modes=udma_supported_modes,
            udma_initial_mode=udma_initial_mode,
            force_pslc=force_pslc,
            write_cache_enable=write_cache_enable,
            pe_cycle_limit=pe_cycle_limit,
            unknown5=unknown5,
            pslc_cache_size=pslc_cache_size,
            identify_vendor_specific=identify_vendor_specific,
            identify_vendor_specific_enable=identify_vendor_specific_enable,
            pslc_cache_size_enable=pslc_cache_size_enable,
            sata_ssc_enable=sata_ssc_enable,
            hipm_enable=hipm_enable,
            dipm_enable=dipm_enable,
            device_apst_enable=device_apst_enable,
            smart_threshold_direction=smart_threshold_direction,
            dipm_threshold=dipm_threshold,
            idle_threshold=idle_threshold,
            idle_enable=idle_enable,
            flush_cache_disable=flush_cache_disable,
            unknown6=unknown6,
            gc_pressure_enable=gc_pressure_enable,
            unknown7=unknown7,
            unknown8=unknown8,
            unknown9=unknown9,
            dco_enable=dco_enable,
            hpa_enable=hpa_enable,
            amac_enable=amac_enable,
            pe_cycle_limit_pslc=pe_cycle_limit_pslc,
            sanitize_enable=sanitize_enable,
            write_uncorrectable_ext_enable=write_uncorrectable_ext_enable,
            zero_ext_enable=zero_ext_enable,
            unknown10=unknown10,
            flush_cache_sync=flush_cache_sync,
            unknown11=unknown11,
            apst_timeout=apst_timeout,
            unknown12=unknown12,
            smart_log_dfh=smart_log_dfh,
            max_pe_cycles_pslc_superblock=max_pe_cycles_pslc_superblock,
            security_enable=security_enable,
            dlmc_enable=dlmc_enable,
            trim_enable=trim_enable,
            dlmc_block_trailing=dlmc_block_trailing,
            unknown13=unknown13,
            wear_level_margin=wear_level_margin,
            unknown14=unknown14,
            wear_level_pslc_interval=wear_level_pslc_interval,
            unknown15=unknown15,
            selftest_enable=selftest_enable,
            protected_allow_write=protected_allow_write,
            hw_security_erase1_mode=hw_security_erase1_mode,
            selftest_extended_untimed=selftest_extended_untimed,
            unknown16=unknown16,
            protected_info_enable=protected_info_enable,
            firmware_protected=firmware_protected,
            model_protected=model_protected,
            unknown17=unknown17,
            selftest_short_time_limit=selftest_short_time_limit,
            selftest_conveyance_time_limit=selftest_conveyance_time_limit,
            selftest_extended_time_limit=selftest_extended_time_limit,
            offline_data_collection_time_limit=offline_data_collection_time_limit,
            security_erase_always_enhanced=security_erase_always_enhanced,
            hw_security_erase1_polarity=hw_security_erase1_polarity,
            unknown18=unknown18,
            hw_security_erase2_mode=hw_security_erase2_mode,
            hw_security_erase2_polarity=hw_security_erase2_polarity,
            brand_17h_cmd_test=brand_17h_cmd_test,
            unknown19=unknown19,
            ftl_force_reserve_blocks=ftl_force_reserve_blocks,
            unknown20=unknown20,
            vuc_6fh_secure_erase_enable=vuc_6fh_secure_erase_enable,
            unknown21=unknown21,
        )

    def __bytes__(self) -> bytes:
        """Pack info block into bytes.

        Returns:
            Bytes.

        """
        serial_raw: bytes = identify.encode_string(self.serial, self._SERIAL_SIZE)
        model_raw: bytes = identify.encode_string(self.model, self._MODEL_SIZE)

        firmware_enable_raw: int = s11_data.bool_pack(self.firmware_enable)
        firmware_raw: bytes = (
            identify.encode_string(self.firmware, self._FIRMWARE_SIZE)
            if self.firmware is not None
            else bytes(self._FIRMWARE_SIZE)
        )

        brand_raw: int = int(self.brand)
        wwn_enable_raw: int = self._optional_bool_pack(self.wwn_enable)
        ce_limit_raw: int = self.ce_limit or 0

        wwn_raw: bytes = (
            bytes(self.wwn) if self.wwn is not None else bytes(identify.WWN.SIZE)
        )

        form_factor_raw: int = int(self.form_factor) if self.form_factor else 0
        addressable_sectors_raw: int = self.addressable_sectors or 0
        interleave_raw: int = int(self.interleave) if self.interleave else 0

        flash_interface_raw: int = (
            int(self.flash_interface) if self.flash_interface else 0
        )

        temperature_sensor_raw: int = (
            int(self.temperature_sensor) if self.temperature_sensor else 0
        )

        devslp_enable_raw: int
        ncq_enable_raw: int
        lba48_enable_raw: int
        dma_modes_enable_raw: int
        force_pslc_raw: int
        write_cache_enable_raw: int
        (
            devslp_enable_raw,
            ncq_enable_raw,
            lba48_enable_raw,
            dma_modes_enable_raw,
            force_pslc_raw,
            write_cache_enable_raw,
        ) = (
            self._optional_bool_pack(x)
            for x in (
                self.devslp_enable,
                self.ncq_enable,
                self.lba48_enable,
                self.dma_modes_enable,
                self.force_pslc,
                self.write_cache_enable,
            )
        )

        pe_cycle_limit_raw: int = self.pe_cycle_limit or 0

        identify_vendor_specific_enable_raw: int
        sata_ssc_enable_raw: int
        hipm_enable_raw: int
        dipm_enable_raw: int
        device_apst_enable_raw: int
        (
            identify_vendor_specific_enable_raw,
            sata_ssc_enable_raw,
            hipm_enable_raw,
            dipm_enable_raw,
            device_apst_enable_raw,
        ) = (
            self._optional_bool_pack(x)
            for x in (
                self.identify_vendor_specific_enable,
                self.sata_ssc_enable,
                self.hipm_enable,
                self.dipm_enable,
                self.device_apst_enable,
            )
        )

        dipm_threshold_raw: int = self.dipm_threshold or 0
        idle_threshold_raw: int = self.idle_threshold or 0

        idle_enable_raw: int
        flush_cache_disable_raw: int
        dco_enable_raw: int
        hpa_enable_raw: int
        amac_enable_raw: int
        (
            idle_enable_raw,
            flush_cache_disable_raw,
            dco_enable_raw,
            hpa_enable_raw,
            amac_enable_raw,
        ) = (
            self._optional_bool_pack(x)
            for x in (
                self.idle_enable,
                self.flush_cache_disable,
                self.dco_enable,
                self.hpa_enable,
                self.amac_enable,
            )
        )

        pe_cycle_limit_pslc_raw: int = self.pe_cycle_limit_pslc or 0

        sanitize_enable_raw: int
        write_uncorrectable_ext_enable_raw: int
        zero_ext_enable_raw: int
        flush_cache_sync_raw: int
        (
            sanitize_enable_raw,
            write_uncorrectable_ext_enable_raw,
            zero_ext_enable_raw,
            flush_cache_sync_raw,
        ) = (
            self._optional_bool_pack(x)
            for x in (
                self.sanitize_enable,
                self.write_uncorrectable_ext_enable,
                self.zero_ext_enable,
                self.flush_cache_sync,
            )
        )

        apst_timeout_raw: int = self.apst_timeout or 0
        smart_log_dfh_raw: bytes = self.smart_log_dfh.encode()
        max_pe_cycles_pslc_superblock_raw: int = self.max_pe_cycles_pslc_superblock or 0

        security_enable_raw: int
        dlmc_enable_raw: int
        trim_enable_raw: int
        dlmc_block_trailing_raw: int
        (
            security_enable_raw,
            dlmc_enable_raw,
            trim_enable_raw,
            dlmc_block_trailing_raw,
        ) = (
            self._optional_bool_pack(x)
            for x in (
                self.security_enable,
                self.dlmc_enable,
                self.trim_enable,
                self.dlmc_block_trailing,
            )
        )

        wear_level_margin_raw: int = self.wear_level_margin or 0
        wear_level_pslc_interval_raw: int = self.wear_level_pslc_interval or 0

        selftest_enable_raw: int
        protected_allow_write_raw: int
        (
            selftest_enable_raw,
            protected_allow_write_raw,
        ) = (
            self._optional_bool_pack(x)
            for x in (
                self.selftest_enable,
                self.protected_allow_write,
            )
        )

        hw_security_erase1_mode_raw: int = self.hw_security_erase1_mode or 0

        selftest_extended_untimed_raw: int = self._optional_bool_pack(
            self.selftest_extended_untimed,
        )

        protected_info_enable_raw: int = s11_data.bool_pack(self.protected_info_enable)

        firmware_protected_raw: bytes
        model_protected_raw: bytes
        firmware_protected_raw, model_protected_raw = (
            (identify.encode_string(value, length) if value else bytes(length))
            for value, length in (
                (self.firmware_protected, self._FIRMWARE_SIZE),
                (self.model_protected, self._MODEL_PROTECTED_SIZE),
            )
        )

        selftest_short_time_limit_raw: int = self.selftest_short_time_limit or 0

        selftest_conveyance_time_limit_raw: int = (
            self.selftest_conveyance_time_limit or 0
        )

        selftest_extended_time_limit_raw: int = self.selftest_extended_time_limit or 0

        offline_data_collection_time_limit_raw: int = (
            self.offline_data_collection_time_limit or 0
        )

        security_erase_always_enhanced_raw: int = self._optional_bool_pack(
            self.security_erase_always_enhanced,
        )

        hw_security_erase2_mode_raw: int = self.hw_security_erase2_mode or 0

        return self._STRUCT.pack(
            self._MAGIC,
            self.unknown1,
            serial_raw,
            model_raw,
            firmware_enable_raw,
            firmware_raw,
            brand_raw,
            wwn_enable_raw,
            ce_limit_raw,
            wwn_raw,
            form_factor_raw,
            self.unknown2,
            addressable_sectors_raw,
            interleave_raw,
            self.unknown3,
            flash_interface_raw,
            self.unknown4,
            temperature_sensor_raw,
            devslp_enable_raw,
            ncq_enable_raw,
            lba48_enable_raw,
            dma_modes_enable_raw,
            self.mwdma_supported_modes,
            self.mwdma_initial_mode,
            self.udma_supported_modes,
            self.udma_initial_mode,
            force_pslc_raw,
            write_cache_enable_raw,
            pe_cycle_limit_raw,
            self.unknown5,
            self.pslc_cache_size,
            self.identify_vendor_specific,
            identify_vendor_specific_enable_raw,
            self.pslc_cache_size_enable,
            sata_ssc_enable_raw,
            hipm_enable_raw,
            dipm_enable_raw,
            device_apst_enable_raw,
            self.smart_threshold_direction,
            dipm_threshold_raw,
            idle_threshold_raw,
            idle_enable_raw,
            flush_cache_disable_raw,
            self.unknown6,
            self.gc_pressure_enable,
            self.unknown7,
            self.unknown8,
            self.unknown9,
            dco_enable_raw,
            hpa_enable_raw,
            amac_enable_raw,
            pe_cycle_limit_pslc_raw,
            sanitize_enable_raw,
            write_uncorrectable_ext_enable_raw,
            zero_ext_enable_raw,
            self.unknown10,
            flush_cache_sync_raw,
            self.unknown11,
            apst_timeout_raw,
            self.unknown12,
            smart_log_dfh_raw,
            max_pe_cycles_pslc_superblock_raw,
            security_enable_raw,
            dlmc_enable_raw,
            trim_enable_raw,
            dlmc_block_trailing_raw,
            self.unknown13,
            wear_level_margin_raw,
            self.unknown14,
            wear_level_pslc_interval_raw,
            self.unknown15,
            selftest_enable_raw,
            protected_allow_write_raw,
            hw_security_erase1_mode_raw,
            selftest_extended_untimed_raw,
            self.unknown16,
            protected_info_enable_raw,
            firmware_protected_raw,
            model_protected_raw,
            self.unknown17,
            selftest_short_time_limit_raw,
            selftest_conveyance_time_limit_raw,
            selftest_extended_time_limit_raw,
            offline_data_collection_time_limit_raw,
            security_erase_always_enhanced_raw,
            self.hw_security_erase1_polarity,
            self.unknown18,
            hw_security_erase2_mode_raw,
            self.hw_security_erase2_polarity,
            self.brand_17h_cmd_test,
            self.unknown19,
            self.ftl_force_reserve_blocks,
            self.unknown20,
            self.vuc_6fh_secure_erase_enable,
            self.unknown21,
        )
