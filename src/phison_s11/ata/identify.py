"""ATA IDENTIFY DEVICE parsing."""

import dataclasses
import enum
import struct
from typing import ClassVar, Self, override

from phison_s11.ata import command


def swap_word_bytes(data: bytes | bytearray) -> bytes:
    """Swap bytes within each 16-bit word.

    Args:
        data: Input data.

    Returns:
        Output data.

    """
    out_data: bytearray = bytearray(len(data))
    out_data[0::2] = data[1::2]
    out_data[1::2] = data[0::2]

    return bytes(out_data)


def decode_string(data: bytes | bytearray) -> str:
    """Decode string in IDENTIFY DEVICE format.

    Args:
        data: Data to decode.

    Returns:
        Decoded string.

    """
    return swap_word_bytes(data).decode().rstrip()


def encode_string(value: str, length: int) -> bytes:
    """Encode string in IDENTIFY DEVICE format.

    Args:
        value: String to encode.
        length: Encoded length.

    Returns:
        Encoded data.

    """
    return swap_word_bytes(value.encode().ljust(length, b" ")[:length])


@dataclasses.dataclass(frozen=True)
class GeneralConfig:
    """General config from word 0.

    Attributes:
        atapi: ATAPI device.
        incomplete: Response is incomplete.

    """

    atapi: bool
    incomplete: bool

    @classmethod
    def parse(cls, word0: int) -> Self:
        """Parse general config.

        Args:
            word0: Raw word 0.

        Returns:
            Parsed general config.

        """
        atapi: bool = bool(word0 & (1 << 15))
        incomplete: bool = bool(word0 & (1 << 2))

        return cls(atapi=atapi, incomplete=incomplete)


@dataclasses.dataclass(frozen=True)
class Capabilities:
    """Capabilities from words 49-50.

    Attributes:
        standard_standby_timer: Standby timer values are standard.
        iordy: IORDY supported.
        iordy_disable: IORDY may be disabled.
        lba: LBA supported.
        dma: DMA supported.
        alignment_error_report: Alignment error reporting mode.
        min_standby_timer: Minimum standby timer present.

    """

    standard_standby_timer: bool
    iordy: bool
    iordy_disable: bool
    lba: bool
    dma: bool
    alignment_error_report: int
    min_standby_timer: bool | None

    @classmethod
    def parse(cls, word49: int, word50: int) -> Self:
        """Parse capabilities.

        Args:
            word49: Raw word 49.
            word50: Raw word 50.

        Returns:
            Parsed capabilities.

        """
        word50_valid: bool = word50 >> 14 == 0b01

        standard_standby_timer: bool = bool(word49 & (1 << 13))
        iordy: bool = bool(word49 & (1 << 11))
        iordy_disable: bool = bool(word49 & (1 << 10))
        lba: bool = bool(word49 & (1 << 9))
        dma: bool = bool(word49 & (1 << 8))
        alignment_error_report: int = word49 & 0b11

        min_standby_timer: bool | None = (
            bool(word50 & (1 << 0)) if word50_valid else None
        )

        return cls(
            standard_standby_timer=standard_standby_timer,
            iordy=iordy,
            iordy_disable=iordy_disable,
            lba=lba,
            dma=dma,
            alignment_error_report=alignment_error_report,
            min_standby_timer=min_standby_timer,
        )


@dataclasses.dataclass(frozen=True)
class SanitizeSupported:
    """Sanitize device supported from word 59.

    Attributes:
        block_erase_ext: BLOCK ERASE EXT supported.
        overwrite_ext: OVERWRITE EXT supported.
        crypto_scramble_ext: CRYPTO SCRAMBLE EXT supported.
        sanitize_device: SANITIZE DEVICE supported.
        sanitize_acs3: Sanitize commands per ACS-3.
        sanitize_antifreeze_lock_ext: SANITIZE ANTIFREEZE LOCK EXT supported.

    """

    block_erase_ext: bool
    overwrite_ext: bool
    crypto_scramble_ext: bool
    sanitize_device: bool
    sanitize_acs3: bool
    sanitize_antifreeze_lock_ext: bool

    @classmethod
    def parse(cls, word59: int) -> Self:
        """Parse sanitize device supported from word 59.

        Args:
            word59: Raw word 59.

        Returns:
            Parsed sanitize device supported.

        """
        block_erase_ext: bool = bool(word59 & (1 << 15))
        overwrite_ext: bool = bool(word59 & (1 << 14))
        crypto_scramble_ext: bool = bool(word59 & (1 << 13))
        sanitize_device: bool = bool(word59 & (1 << 12))
        sanitize_acs3: bool = bool(word59 & (1 << 11))
        sanitize_antifreeze_lock_ext: bool = bool(word59 & (1 << 10))

        return cls(
            block_erase_ext=block_erase_ext,
            overwrite_ext=overwrite_ext,
            crypto_scramble_ext=crypto_scramble_ext,
            sanitize_device=sanitize_device,
            sanitize_acs3=sanitize_acs3,
            sanitize_antifreeze_lock_ext=sanitize_antifreeze_lock_ext,
        )


@dataclasses.dataclass(frozen=True)
class MultiwordDMAModes:
    """Multiword DMA modes from word 63.

    Attributes:
        mode2_selected: Mode 2 selected.
        mode1_selected: Mode 1 selected.
        mode0_selected: Mode 0 selected.
        mode2_supported: Mode 2 supported.
        mode1_supported: Mode 1 supported.
        mode0_supported: Mode 0 supported.

    """

    mode2_selected: bool
    mode1_selected: bool
    mode0_selected: bool
    mode2_supported: bool
    mode1_supported: bool
    mode0_supported: bool

    @classmethod
    def parse(cls, word63: int) -> Self:
        """Parse multiword DMA modes.

        Args:
            word63: Raw word 63.

        Returns:
            Parsed multiword DMA modes.

        """
        mode2_selected: bool = bool(word63 & (1 << 10))
        mode1_selected: bool = bool(word63 & (1 << 9))
        mode0_selected: bool = bool(word63 & (1 << 8))
        mode2_supported: bool = bool(word63 & (1 << 2))
        mode1_supported: bool = bool(word63 & (1 << 1))
        mode0_supported: bool = bool(word63 & (1 << 0))

        return cls(
            mode2_selected=mode2_selected,
            mode1_selected=mode1_selected,
            mode0_selected=mode0_selected,
            mode2_supported=mode2_supported,
            mode1_supported=mode1_supported,
            mode0_supported=mode0_supported,
        )


@dataclasses.dataclass(frozen=True)
class PIOModes:
    """PIO modes from word 64.

    Attributes:
        mode4_supported: PIO mode 4 supported.
        mode3_supported: PIO mode 3 supported.

    """

    mode4_supported: bool
    mode3_supported: bool

    @classmethod
    def parse(cls, word64: int) -> Self:
        """Parse PIO modes.

        Args:
            word64: Raw word 64.

        Returns:
            Parsed PIO mode supported.

        """
        mode4_supported: bool = bool(word64 & (1 << 1))
        mode3_supported: bool = bool(word64 & (1 << 0))

        return cls(mode4_supported=mode4_supported, mode3_supported=mode3_supported)


class ZonedCapabilities(enum.IntEnum):
    """Zoned capabilities from word 69.

    Attributes:
        HOST_AWARE: Host aware.
        DEVICE_MANAGED: Device managed.

    """

    HOST_AWARE = 0b1
    DEVICE_MANAGED = 0b10

    @classmethod
    def parse(cls, word69: int) -> Self | None:
        """Parse zoned capabilities.

        Args:
            word69: Raw word 69.

        Returns:
            Parsed zoned capabilities if any.

        """
        raw: int = word69 & 0b11
        return cls(raw) if raw else None


@dataclasses.dataclass(frozen=True)
class AdditionalSupported:
    """Additional supported from word 69.

    Attributes:
        cfast: CFast specification supported.
        drat: Deterministic Read After Trim supported.
        lps_align_error_report: Long Physical Sector alignment error
            reporting control supported.
        read_buffer_dma: READ BUFFER DMA supported.
        write_buffer_dma: WRITE BUFFER DMA supported.
        dlmc_dma: DOWNLOAD MICROCODE DMA supported.
        optional_28bit: Optional 28-bit commands supported.
        rzat: Read zeros after trim.
        encrypted: Device encrypts all user data.
        sector_count_ext: Extended Number of User Addressable Sectors
            is supported.
        write_cache_nv: Write cache is non-volatile.
        zoned: Zoned capabilities.

    """

    cfast: bool
    drat: bool
    lps_align_error_report: bool
    read_buffer_dma: bool
    write_buffer_dma: bool
    dlmc_dma: bool
    optional_28bit: bool
    rzat: bool
    encrypted: bool
    sector_count_ext: bool
    write_cache_nv: bool
    zoned: ZonedCapabilities | None

    @classmethod
    def parse(cls, word69: int) -> Self:
        """Parse additional supported.

        Args:
            word69: Raw word 69 value.

        Returns:
            Parsed additional supported.

        """
        cfast: bool = bool(word69 & (1 << 15))
        drat: bool = bool(word69 & (1 << 14))
        lps_align_error_report: bool = bool(word69 & (1 << 13))
        read_buffer_dma: bool = bool(word69 & (1 << 11))
        write_buffer_dma: bool = bool(word69 & (1 << 10))
        dlmc_dma: bool = bool(word69 & (1 << 8))
        optional_28bit: bool = not bool(word69 & (1 << 6))
        rzat: bool = bool(word69 & (1 << 5))
        encrypted: bool = bool(word69 & (1 << 4))
        sector_count_ext: bool = bool(word69 & (1 << 3))
        write_cache_nv: bool = bool(word69 & (1 << 2))
        zoned: ZonedCapabilities | None = ZonedCapabilities.parse(word69)

        return cls(
            cfast=cfast,
            drat=drat,
            lps_align_error_report=lps_align_error_report,
            read_buffer_dma=read_buffer_dma,
            write_buffer_dma=write_buffer_dma,
            dlmc_dma=dlmc_dma,
            optional_28bit=optional_28bit,
            rzat=rzat,
            encrypted=encrypted,
            sector_count_ext=sector_count_ext,
            write_cache_nv=write_cache_nv,
            zoned=zoned,
        )


@dataclasses.dataclass(frozen=True)
class SataCapabilities:
    """SATA capabilities from word 76.

    Attributes:
        read_log_dma_ext: READ LOG DMA EXT supported.
        device_apst: Device automatic partial to slumber transitions supported.
        host_apst: Host automatic partial to slumber transitions supported.
        ncq_priority: NCQ priority information supported.
        ncq_unload: NCQ unload supported.
        phy_event_counters: Phy event counters supported.
        hipm_receipt: Receipt of host initiated power management
            requests supported.
        ncq: Native Command Queuing supported.
        gen3: 6.0 Gbps signaling supported.
        gen2: 3.0 Gbps signaling supported.
        gen1: 1.5 Gbps signaling supported.

    """

    read_log_dma_ext: bool
    device_apst: bool
    host_apst: bool
    ncq_priority: bool
    ncq_unload: bool
    phy_event_counters: bool
    hipm_receipt: bool
    ncq: bool
    gen3: bool
    gen2: bool
    gen1: bool

    @classmethod
    def parse(cls, word76: int) -> Self | None:
        """Parse SATA capabilities.

        Args:
            word76: Raw word 76.

        Returns:
            Parsed SATA capabilities if any.

        """
        if word76 in (0, 0xFFFF):
            return None

        read_log_dma_ext: bool = bool(word76 & (1 << 15))
        device_apst: bool = bool(word76 & (1 << 14))
        host_apst: bool = bool(word76 & (1 << 13))
        ncq_priority: bool = bool(word76 & (1 << 12))
        ncq_unload: bool = bool(word76 & (1 << 11))
        phy_event_counters: bool = bool(word76 & (1 << 10))
        hipm_receipt: bool = bool(word76 & (1 << 9))
        ncq: bool = bool(word76 & (1 << 8))
        gen3: bool = bool(word76 & (1 << 3))
        gen2: bool = bool(word76 & (1 << 2))
        gen1: bool = bool(word76 & (1 << 1))

        return cls(
            read_log_dma_ext=read_log_dma_ext,
            device_apst=device_apst,
            host_apst=host_apst,
            ncq_priority=ncq_priority,
            ncq_unload=ncq_unload,
            phy_event_counters=phy_event_counters,
            hipm_receipt=hipm_receipt,
            ncq=ncq,
            gen3=gen3,
            gen2=gen2,
            gen1=gen1,
        )


@dataclasses.dataclass(frozen=True)
class SataAdditionalCapabilities:
    """SATA additional capabilities from word 77.

    Attributes:
        power_disable_always_enabled: Power Disable always enabled.
        devslp_to_reducedpwrstate: DevSleep to ReducedPwrState supported.
        fpdma_queued: Supporteds RECEIVE FPDMA QUEUED and SEND FPDMA QUEUED.
        ncq_non_data: NCQ queue management command supported.
        ncq_streaming: NCQ Streaming supported.
        signal_speed: Current negotiated signal speed (0-7).

    """

    power_disable_always_enabled: bool
    devslp_to_reducedpwrstate: bool
    fpdma_queued: bool
    ncq_non_data: bool
    ncq_streaming: bool
    signal_speed: int

    @classmethod
    def parse(cls, word77: int) -> Self:
        """Parse SATA additional capabilities.

        Args:
            word77: Raw word 77.

        Returns:
            Parsed SATA additional capabilities.

        """
        power_disable_always_enabled: bool = bool(word77 & (1 << 8))
        devslp_to_reducedpwrstate: bool = bool(word77 & (1 << 7))
        fpdma_queued: bool = bool(word77 & (1 << 6))
        ncq_non_data: bool = bool(word77 & (1 << 5))
        ncq_streaming: bool = bool(word77 & (1 << 4))
        signal_speed: int = (word77 >> 1) & 0b111

        return cls(
            power_disable_always_enabled=power_disable_always_enabled,
            devslp_to_reducedpwrstate=devslp_to_reducedpwrstate,
            fpdma_queued=fpdma_queued,
            ncq_non_data=ncq_non_data,
            ncq_streaming=ncq_streaming,
            signal_speed=signal_speed,
        )


@dataclasses.dataclass(frozen=True)
class SataFeaturesSupported:
    """SATA features supported from word 78.

    Attributes:
        power_disable: Power disable.
        rebuild_assist: Rebuild assist.
        hybrid_information: Hybrid information.
        devslp: Device sleep.
        ncq_autosense: NCQ autosense.
        ssp: Software Settings Preservation.
        hardware_feature_control: Hardware feature control.
        inorder_delivery: In-order data delivery.
        dipm: Device Initiated Power Management.
        dma_setup_autoactivate: DMA setup auto-activate.
        nonzero_buffer_offset: Non-zero buffer offsets.

    """

    power_disable: bool
    rebuild_assist: bool
    hybrid_information: bool
    devslp: bool
    ncq_autosense: bool
    ssp: bool
    hardware_feature_control: bool
    inorder_delivery: bool
    dipm: bool
    dma_setup_autoactivate: bool
    nonzero_buffer_offset: bool

    @classmethod
    def parse(cls, word78: int) -> Self:
        """Parse SATA features supported.

        Args:
            word78: Raw word 78.

        Returns:
            Parsed SATA features supported.

        """
        power_disable: bool = bool(word78 & (1 << 12))
        rebuild_assist: bool = bool(word78 & (1 << 11))
        hybrid_information: bool = bool(word78 & (1 << 9))
        devslp: bool = bool(word78 & (1 << 8))
        ncq_autosense: bool = bool(word78 & (1 << 7))
        ssp: bool = bool(word78 & (1 << 6))
        hardware_feature_control: bool = bool(word78 & (1 << 5))
        inorder_delivery: bool = bool(word78 & (1 << 4))
        dipm: bool = bool(word78 & (1 << 3))
        dma_setup_autoactivate: bool = bool(word78 & (1 << 2))
        nonzero_buffer_offset: bool = bool(word78 & (1 << 1))

        return cls(
            power_disable=power_disable,
            rebuild_assist=rebuild_assist,
            hybrid_information=hybrid_information,
            devslp=devslp,
            ncq_autosense=ncq_autosense,
            ssp=ssp,
            hardware_feature_control=hardware_feature_control,
            inorder_delivery=inorder_delivery,
            dipm=dipm,
            dma_setup_autoactivate=dma_setup_autoactivate,
            nonzero_buffer_offset=nonzero_buffer_offset,
        )


@dataclasses.dataclass(frozen=True)
class SataFeaturesEnabled:
    """SATA features enabled from word 79.

    Attributes:
        rebuild_assist: Rebuild assist.
        power_disable: Power disable.
        hybrid_information: Hybrid information.
        devslp: Device sleep.
        apst: Automatic Partial to Slumber Transitions.
        ssp: Software Settings Preservation.
        hardware_feature_control: Hardware feature control.
        inorder_delivery: In-order data delivery.
        dipm: Device Initiated Power Management.
        dma_setup_autoactivate: DMA setup auto-activate.
        nonzero_buffer_offset: Non-zero buffer offsets.

    """

    rebuild_assist: bool
    power_disable: bool
    hybrid_information: bool
    devslp: bool
    apst: bool
    ssp: bool
    hardware_feature_control: bool
    inorder_delivery: bool
    dipm: bool
    dma_setup_autoactivate: bool
    nonzero_buffer_offset: bool

    @classmethod
    def parse(cls, word79: int) -> Self:
        """Parse SATA features enabled.

        Args:
            word79: Raw word 79.

        Returns:
            Parsed SATA features enabled.

        """
        rebuild_assist: bool = bool(word79 & (1 << 11))
        power_disable: bool = bool(word79 & (1 << 10))
        hybrid_information: bool = bool(word79 & (1 << 9))
        devslp: bool = bool(word79 & (1 << 8))
        apst: bool = bool(word79 & (1 << 7))
        ssp: bool = bool(word79 & (1 << 6))
        hardware_feature_control: bool = bool(word79 & (1 << 5))
        inorder_delivery: bool = bool(word79 & (1 << 4))
        dipm: bool = bool(word79 & (1 << 3))
        dma_setup_autoactivate: bool = bool(word79 & (1 << 2))
        nonzero_buffer_offset: bool = bool(word79 & (1 << 1))

        return cls(
            rebuild_assist=rebuild_assist,
            power_disable=power_disable,
            hybrid_information=hybrid_information,
            devslp=devslp,
            apst=apst,
            ssp=ssp,
            hardware_feature_control=hardware_feature_control,
            inorder_delivery=inorder_delivery,
            dipm=dipm,
            dma_setup_autoactivate=dma_setup_autoactivate,
            nonzero_buffer_offset=nonzero_buffer_offset,
        )


@dataclasses.dataclass(frozen=True)
class MajorVersion:
    """Major version from word 80.

    Attributes:
        acs_5: ACS-5.
        acs_4: ACS-4.
        acs_3: ACS-3.
        acs_2: ACS-2.
        ata8_acs: ATA8-ACS.
        ata_atapi_7: ATA/ATAPI-7.
        ata_atapi_6: ATA/ATAPI-6.
        ata_atapi_5: ATA/ATAPI-5.
        ata_atapi_4: ATA/ATAPI-4.

    """

    acs_5: bool
    acs_4: bool
    acs_3: bool
    acs_2: bool
    ata8_acs: bool
    ata_atapi_7: bool
    ata_atapi_6: bool
    ata_atapi_5: bool
    ata_atapi_4: bool

    @classmethod
    def parse(cls, word80: int) -> Self | None:
        """Parse major version.

        Args:
            word80: Raw word 80.

        Returns:
            Parsed major version if any.

        """
        if word80 in (0, 0xFFFF):
            return None

        acs_5: bool = bool(word80 & (1 << 12))
        acs_4: bool = bool(word80 & (1 << 11))
        acs_3: bool = bool(word80 & (1 << 10))
        acs_2: bool = bool(word80 & (1 << 9))
        ata8_acs: bool = bool(word80 & (1 << 8))
        ata_atapi_7: bool = bool(word80 & (1 << 7))
        ata_atapi_6: bool = bool(word80 & (1 << 6))
        ata_atapi_5: bool = bool(word80 & (1 << 5))
        ata_atapi_4: bool = bool(word80 & (1 << 4))

        return cls(
            acs_5=acs_5,
            acs_4=acs_4,
            acs_3=acs_3,
            acs_2=acs_2,
            ata8_acs=ata8_acs,
            ata_atapi_7=ata_atapi_7,
            ata_atapi_6=ata_atapi_6,
            ata_atapi_5=ata_atapi_5,
            ata_atapi_4=ata_atapi_4,
        )


class MinorVersion(enum.IntEnum):
    """Minor version from word 81.

    Attributes:
        ATA_ATAPI_4_R6: ATA/ATAPI-4 X3T13 1153D revision 6.
        ATA_ATAPI_4_R13: ATA/ATAPI-4 T13 1153D revision 13.
        ATA_ATAPI_4_R7: ATA/ATAPI-4 X3T13 1153D revision 7.
        ATA_ATAPI_4_R18: ATA/ATAPI-4 T13 1153D revision 18.
        ATA_ATAPI_4_R15: ATA/ATAPI-4 T13 1153D revision 15.
        ATA_ATAPI_4_PUB: ATA/ATAPI-4 published.
        ATA_ATAPI_5_R3: ATA/ATAPI-5 T13 1321D revision 3.
        ATA_ATAPI_4_R14: ATA/ATAPI-4 T13 1153D revision 14.
        ATA_ATAPI_5_R1: ATA/ATAPI-5 T13 1321D revision 1.
        ATA_ATAPI_5_PUB: ATA/ATAPI-5 published.
        ATA_ATAPI_4_R17: ATA/ATAPI-4 T13 1153D revision 17.
        ATA_ATAPI_6_R0: ATA/ATAPI-6 T13 1410D revision 0.
        ATA_ATAPI_6_R3A: ATA/ATAPI-6 T13 1410D revision 3a.
        ATA_ATAPI_7_R1: ATA/ATAPI-7 T13 1532D revision 1.
        ATA_ATAPI_6_R2: ATA/ATAPI-6 T13 1410D revision 2.
        ATA_ATAPI_6_R1: ATA/ATAPI-6 T13 1410D revision 1.
        ATA_ATAPI_7_PUB: ATA/ATAPI-7 published.
        ATA_ATAPI_7_R0: ATA/ATAPI-7 T13 1532D revision 0.
        ACS_3_REV_3B: ACS-3 Revision 3b.
        ATA_ATAPI_7_R4A: ATA/ATAPI-7 T13 1532D revision 4a.
        ATA_ATAPI_6_PUB: ATA/ATAPI-6 published.
        ATA8_ACS_3C: ATA8-ACS version 3c.
        ATA8_ACS_6: ATA8-ACS version 6.
        ATA8_ACS_4: ATA8-ACS version 4.
        ACS_2_REV_2: ACS-2 Revision 2.
        ATA8_ACS_3E: ATA8-ACS version 3e.
        ATA8_ACS_4C: ATA8-ACS version 4c.
        ATA8_ACS_3F: ATA8-ACS version 3f.
        ATA8_ACS_3B: ATA8-ACS version 3b.
        ACS_4_REV_5: ACS-4 Revision 5.
        ACS_3_REV_5: ACS-3 Revision 5.
        ACS_2_PUB: ACS-2 published.
        ATA8_ACS_2D: ATA8-ACS version 2d.
        ACS_3_PUB: ACS-3 published.
        ACS_2_REV_3: ACS-2 Revision 3.
        ACS_3_REV_4: ACS-3 Revision 4.

    """

    ATA_ATAPI_4_R6 = 0xD
    ATA_ATAPI_4_R13 = 0xE
    ATA_ATAPI_4_R7 = 0xF
    ATA_ATAPI_4_R18 = 0x10
    ATA_ATAPI_4_R15 = 0x11
    ATA_ATAPI_4_PUB = 0x12
    ATA_ATAPI_5_R3 = 0x13
    ATA_ATAPI_4_R14 = 0x14
    ATA_ATAPI_5_R1 = 0x15
    ATA_ATAPI_5_PUB = 0x16
    ATA_ATAPI_4_R17 = 0x17
    ATA_ATAPI_6_R0 = 0x18
    ATA_ATAPI_6_R3A = 0x19
    ATA_ATAPI_7_R1 = 0x1A
    ATA_ATAPI_6_R2 = 0x1B
    ATA_ATAPI_6_R1 = 0x1C
    ATA_ATAPI_7_PUB = 0x1D
    ATA_ATAPI_7_R0 = 0x1E
    ACS_3_REV_3B = 0x1F
    ATA_ATAPI_7_R4A = 0x21
    ATA_ATAPI_6_PUB = 0x22
    ATA8_ACS_3C = 0x27
    ATA8_ACS_6 = 0x28
    ATA8_ACS_4 = 0x29
    ACS_2_REV_2 = 0x31
    ATA8_ACS_3E = 0x33
    ATA8_ACS_4C = 0x39
    ATA8_ACS_3F = 0x42
    ATA8_ACS_3B = 0x52
    ACS_4_REV_5 = 0x5E
    ACS_3_REV_5 = 0x6D
    ACS_2_PUB = 0x82
    ATA8_ACS_2D = 0x107
    ACS_3_PUB = 0x10A
    ACS_2_REV_3 = 0x110
    ACS_3_REV_4 = 0x11B

    @classmethod
    def parse(cls, word81: int) -> Self | None:
        """Parse minor version.

        Args:
            word81: Raw word 81.

        Returns:
            Parsed minor version if any.

        """
        return None if word81 in (0, 0xFFFF) else cls(word81)


@dataclasses.dataclass(frozen=True)
class _Features:
    """Base for feature set fields.

    Attributes:
        nop: NOP feature if any.
        read_buffer: READ BUFFER feature if any.
        write_buffer: WRITE BUFFER feature if any.
        device_reset: DEVICE RESET feature if any.
        read_lookahead: Read look-ahead feature if any.
        volatile_write_cache: Volatile write cache feature if any.
        packet: PACKET feature set if any.
        power_management: Power Management feature set if any.
        security: Security feature set if any.
        smart: SMART feature set if any.
        flush_cache_ext: FLUSH CACHE EXT feature if any.
        flush_cache: FLUSH CACHE feature if any.
        address_48bit: 48-bit Address feature set if any.
        set_features_required: SET FEATURES required to spin-up feature if any.
        puis: Power-Up In Standby feature set if any.
        apm: Advanced Power Management feature set if any.
        cfa: CFA feature set if any.
        dlmc: DOWNLOAD MICROCODE feature if any.
        idle_immediate_unload: IDLE IMMEDIATE with UNLOAD feature if any.
        wwn: World Wide Name feature if any.
        write_dma_fua_ext: WRITE DMA FUA EXT feature if any.
        gpl: General Purpose Logging feature set if any.
        smart_self_test: SMART self-test feature if any.
        smart_error_log: SMART error logging feature if any.
        dsn: Device Statistics Notification feature if any.
        epc: Extended Power Conditions feature if any.
        sense: Sense data reporting feature if any.
        freefall_control: Free-fall Control feature set if any.
        dlmc_mode3: DOWNLOAD MICROCODE mode 3 feature if any.
        read_write_log_dma_ext: READ/WRITE LOG DMA EXT feature if any.
        write_uncorrectable_ext: WRITE UNCORRECTABLE EXT feature if any.
        wrv: Write-Read-Verify feature if any.

    """

    nop: bool | None
    read_buffer: bool | None
    write_buffer: bool | None
    device_reset: bool | None
    read_lookahead: bool | None
    volatile_write_cache: bool | None
    packet: bool | None
    power_management: bool | None
    security: bool | None
    smart: bool | None
    flush_cache_ext: bool | None
    flush_cache: bool | None
    address_48bit: bool | None
    set_features_required: bool | None
    puis: bool | None
    apm: bool | None
    cfa: bool | None
    dlmc: bool | None
    idle_immediate_unload: bool | None
    wwn: bool | None
    write_dma_fua_ext: bool | None
    gpl: bool | None
    smart_self_test: bool | None
    smart_error_log: bool | None
    dsn: bool | None
    epc: bool | None
    sense: bool | None
    freefall_control: bool | None
    dlmc_mode3: bool | None
    read_write_log_dma_ext: bool | None
    write_uncorrectable_ext: bool | None
    wrv: bool | None

    @classmethod
    def parse(
        cls,
        word82_or_85: int | None,
        word83_or_86: int | None,
        word84_or_87: int | None,
        word119_or_120: int | None,
    ) -> Self:
        """Parse feature set words.

        Args:
            word82_or_85: First feature word (word 82 or 85) if any.
            word83_or_86: Second feature word (word 83 or 86) if any.
            word84_or_87: Third feature word (word 84 or 87) if any.
            word119_or_120: Fourth feature word (word 119 or 120) if any.

        Returns:
            Parsed features.

        """
        nop: bool | None = (
            None if word82_or_85 is None else bool(word82_or_85 & (1 << 14))
        )
        read_buffer: bool | None = (
            None if word82_or_85 is None else bool(word82_or_85 & (1 << 13))
        )
        write_buffer: bool | None = (
            None if word82_or_85 is None else bool(word82_or_85 & (1 << 12))
        )
        device_reset: bool | None = (
            None if word82_or_85 is None else bool(word82_or_85 & (1 << 9))
        )
        read_lookahead: bool | None = (
            None if word82_or_85 is None else bool(word82_or_85 & (1 << 6))
        )
        volatile_write_cache: bool | None = (
            None if word82_or_85 is None else bool(word82_or_85 & (1 << 5))
        )
        packet: bool | None = (
            None if word82_or_85 is None else bool(word82_or_85 & (1 << 4))
        )
        power_management: bool | None = (
            None if word82_or_85 is None else bool(word82_or_85 & (1 << 3))
        )
        security: bool | None = (
            None if word82_or_85 is None else bool(word82_or_85 & (1 << 1))
        )
        smart: bool | None = (
            None if word82_or_85 is None else bool(word82_or_85 & (1 << 0))
        )

        flush_cache_ext: bool | None = (
            None if word83_or_86 is None else bool(word83_or_86 & (1 << 13))
        )
        flush_cache: bool | None = (
            None if word83_or_86 is None else bool(word83_or_86 & (1 << 12))
        )
        address_48bit: bool | None = (
            None if word83_or_86 is None else bool(word83_or_86 & (1 << 10))
        )
        set_features_required: bool | None = (
            None if word83_or_86 is None else bool(word83_or_86 & (1 << 6))
        )
        puis: bool | None = (
            None if word83_or_86 is None else bool(word83_or_86 & (1 << 5))
        )
        apm: bool | None = (
            None if word83_or_86 is None else bool(word83_or_86 & (1 << 3))
        )
        cfa: bool | None = (
            None if word83_or_86 is None else bool(word83_or_86 & (1 << 2))
        )
        dlmc: bool | None = (
            None if word83_or_86 is None else bool(word83_or_86 & (1 << 0))
        )

        idle_immediate_unload: bool | None = (
            None if word84_or_87 is None else bool(word84_or_87 & (1 << 13))
        )
        wwn: bool | None = (
            None if word84_or_87 is None else bool(word84_or_87 & (1 << 8))
        )
        write_dma_fua_ext: bool | None = (
            None if word84_or_87 is None else bool(word84_or_87 & (1 << 6))
        )
        gpl: bool | None = (
            None if word84_or_87 is None else bool(word84_or_87 & (1 << 5))
        )
        smart_self_test: bool | None = (
            None if word84_or_87 is None else bool(word84_or_87 & (1 << 1))
        )
        smart_error_log: bool | None = (
            None if word84_or_87 is None else bool(word84_or_87 & (1 << 0))
        )

        dsn: bool | None = (
            None if word119_or_120 is None else bool(word119_or_120 & (1 << 9))
        )
        epc: bool | None = (
            None if word119_or_120 is None else bool(word119_or_120 & (1 << 7))
        )
        sense: bool | None = (
            None if word119_or_120 is None else bool(word119_or_120 & (1 << 6))
        )
        freefall_control: bool | None = (
            None if word119_or_120 is None else bool(word119_or_120 & (1 << 5))
        )
        dlmc_mode3: bool | None = (
            None if word119_or_120 is None else bool(word119_or_120 & (1 << 4))
        )
        read_write_log_dma_ext: bool | None = (
            None if word119_or_120 is None else bool(word119_or_120 & (1 << 3))
        )
        write_uncorrectable_ext: bool | None = (
            None if word119_or_120 is None else bool(word119_or_120 & (1 << 2))
        )
        wrv: bool | None = (
            None if word119_or_120 is None else bool(word119_or_120 & (1 << 1))
        )

        return cls(
            nop=nop,
            read_buffer=read_buffer,
            write_buffer=write_buffer,
            device_reset=device_reset,
            read_lookahead=read_lookahead,
            volatile_write_cache=volatile_write_cache,
            packet=packet,
            power_management=power_management,
            security=security,
            smart=smart,
            flush_cache_ext=flush_cache_ext,
            flush_cache=flush_cache,
            address_48bit=address_48bit,
            set_features_required=set_features_required,
            puis=puis,
            apm=apm,
            cfa=cfa,
            dlmc=dlmc,
            idle_immediate_unload=idle_immediate_unload,
            wwn=wwn,
            write_dma_fua_ext=write_dma_fua_ext,
            gpl=gpl,
            smart_self_test=smart_self_test,
            smart_error_log=smart_error_log,
            dsn=dsn,
            epc=epc,
            sense=sense,
            freefall_control=freefall_control,
            dlmc_mode3=dlmc_mode3,
            read_write_log_dma_ext=read_write_log_dma_ext,
            write_uncorrectable_ext=write_uncorrectable_ext,
            wrv=wrv,
        )


@dataclasses.dataclass(frozen=True)
class FeaturesSupported(_Features):
    """Commands and feature sets supported from words 82-84 and 119.

    Attributes:
        streaming: Streaming feature if any.
        amac: Accessible Max Address Configuration feature set if any.

    """

    streaming: bool | None
    amac: bool | None

    @classmethod
    def parse(
        cls,
        word82: int | None,
        word83: int | None,
        word84: int | None,
        word119: int | None,
    ) -> Self:
        """Parse supported features from words 82-84 and 119.

        Args:
            word82: Raw word 82 if any.
            word83: Raw word 83 if any.
            word84: Raw word 84 if any.
            word119: Raw word 119 if any.

        Returns:
            Parsed supported feature sets.

        """
        words82_83_valid: bool = word83 is not None and word83 >> 14 == 0b01
        if not words82_83_valid:
            word82 = None
            word83 = None

        word84_valid: bool = word84 is not None and word84 >> 14 == 0b01
        if not word84_valid:
            word84 = None

        word119_valid: bool = word119 is not None and word119 >> 14 == 0b01
        if not word119_valid:
            word119 = None

        streaming: bool | None = None if word84 is None else bool(word84 & (1 << 4))
        amac: bool | None = None if word119 is None else bool(word119 & (1 << 8))

        base: _Features = _Features.parse(
            word82,
            word83,
            word84,
            word119,
        )

        return cls(
            **{f.name: getattr(base, f.name) for f in dataclasses.fields(base)},
            streaming=streaming,
            amac=amac,
        )


@dataclasses.dataclass(frozen=True)
class FeaturesEnabled(_Features):
    """Commands and feature sets enabled from words 85-87 and 120.

    Attributes:
        words_119_120_valid: Words 119-120 are valid if any.
        media_serial_valid: Media serial is valid if any.

    """

    words_119_120_valid: bool | None
    media_serial_valid: bool | None

    @classmethod
    def parse(
        cls,
        word85: int | None,
        word86: int | None,
        word87: int | None,
        word120: int | None,
    ) -> Self:
        """Parse features enabled.

        Args:
            word85: Raw word 85 if any.
            word86: Raw word 86 if any.
            word87: Raw word 87 if any.
            word120: Raw word 120 if any.

        Returns:
            Parsed enabled feature sets.

        """
        words85_to_87_valid: bool = word87 is not None and word87 >> 14 == 0b01
        if not words85_to_87_valid:
            word85 = None
            word86 = None
            word87 = None

        words_119_120_valid: bool | None = (
            None if word86 is None else bool(word86 & (1 << 15))
        )

        word120_valid: bool = (
            bool(words_119_120_valid) and word120 is not None and word120 >> 14 == 0b01
        )
        if not word120_valid:
            word120 = None

        media_serial_valid: bool | None = (
            None if word87 is None else bool(word87 & (1 << 2))
        )

        base: _Features = _Features.parse(
            word85,
            word86,
            word87,
            word120,
        )

        return cls(
            **{x.name: getattr(base, x.name) for x in dataclasses.fields(base)},
            words_119_120_valid=words_119_120_valid,
            media_serial_valid=media_serial_valid,
        )


@dataclasses.dataclass(frozen=True)
class UltraDMAModes:
    """Ultra DMA mode supported and selection from word 88.

    Attributes:
        mode6_selected: Mode 6 selected.
        mode5_selected: Mode 5 selected.
        mode4_selected: Mode 4 selected.
        mode3_selected: Mode 3 selected.
        mode2_selected: Mode 2 selected.
        mode1_selected: Mode 1 selected.
        mode0_selected: Mode 0 selected.
        mode6_supported: Mode 6 supported.
        mode5_supported: Mode 5 supported.
        mode4_supported: Mode 4 supported.
        mode3_supported: Mode 3 supported.
        mode2_supported: Mode 2 supported.
        mode1_supported: Mode 1 supported.
        mode0_supported: Mode 0 supported.

    """

    mode6_selected: bool
    mode5_selected: bool
    mode4_selected: bool
    mode3_selected: bool
    mode2_selected: bool
    mode1_selected: bool
    mode0_selected: bool
    mode6_supported: bool
    mode5_supported: bool
    mode4_supported: bool
    mode3_supported: bool
    mode2_supported: bool
    mode1_supported: bool
    mode0_supported: bool

    @classmethod
    def parse(cls, word88: int) -> Self:
        """Parse Ultra DMA modes.

        Args:
            word88: Raw word 88.

        Returns:
            Parsed Ultra DMA modes.

        """
        mode6_selected: bool = bool(word88 & (1 << 14))
        mode5_selected: bool = bool(word88 & (1 << 13))
        mode4_selected: bool = bool(word88 & (1 << 12))
        mode3_selected: bool = bool(word88 & (1 << 11))
        mode2_selected: bool = bool(word88 & (1 << 10))
        mode1_selected: bool = bool(word88 & (1 << 9))
        mode0_selected: bool = bool(word88 & (1 << 8))

        mode6_supported: bool = bool(word88 & (1 << 6))
        mode5_supported: bool = bool(word88 & (1 << 5))
        mode4_supported: bool = bool(word88 & (1 << 4))
        mode3_supported: bool = bool(word88 & (1 << 3))
        mode2_supported: bool = bool(word88 & (1 << 2))
        mode1_supported: bool = bool(word88 & (1 << 1))
        mode0_supported: bool = bool(word88 & (1 << 0))

        return cls(
            mode6_selected=mode6_selected,
            mode5_selected=mode5_selected,
            mode4_selected=mode4_selected,
            mode3_selected=mode3_selected,
            mode2_selected=mode2_selected,
            mode1_selected=mode1_selected,
            mode0_selected=mode0_selected,
            mode6_supported=mode6_supported,
            mode5_supported=mode5_supported,
            mode4_supported=mode4_supported,
            mode3_supported=mode3_supported,
            mode2_supported=mode2_supported,
            mode1_supported=mode1_supported,
            mode0_supported=mode0_supported,
        )


@dataclasses.dataclass(frozen=True)
class HardwareResetResult:
    """Hardware reset result from word 93.

    Attributes:
        cblid_above_vihb: CBLID- above ViHB.
        dev1_pdiag_asserted: Device 1 asserted PDIAG-.
        dev1_detection_method: Device 1 detection method (0-3).
        dev0_responds_when_dev1_selected: Device 0 responds when
            device 1 is selected.
        dev0_dasp_asserted: Device 0 detected assertion of DASP-.
        dev0_pdiag_asserted: Device 0 detected assertion of PDIAG-.
        dev0_passed_diagnostics: Device 0 passed diagnostics.
        dev0_detection_method: Device 0 detection method (0-3).

    """

    cblid_above_vihb: bool
    dev1_pdiag_asserted: bool
    dev1_detection_method: int
    dev0_responds_when_dev1_selected: bool
    dev0_dasp_asserted: bool
    dev0_pdiag_asserted: bool
    dev0_passed_diagnostics: bool
    dev0_detection_method: int

    @classmethod
    def parse(cls, word93: int) -> Self | None:
        """Parse hardware reset result.

        Args:
            word93: Raw word 93.

        Returns:
            Parsed hardware reset result if any.

        """
        if word93 >> 14 != 0b01:
            return None

        cblid_above_vihb: bool = bool(word93 & (1 << 13))
        dev1_pdiag_asserted: bool = bool(word93 & (1 << 11))
        dev1_detection_method: int = (word93 >> 9) & 0b11
        dev0_responds_when_dev1_selected: bool = bool(word93 & (1 << 6))
        dev0_dasp_asserted: bool = bool(word93 & (1 << 5))
        dev0_pdiag_asserted: bool = bool(word93 & (1 << 4))
        dev0_passed_diagnostics: bool = bool(word93 & (1 << 3))
        dev0_detection_method: int = (word93 >> 1) & 0b11

        return cls(
            cblid_above_vihb=cblid_above_vihb,
            dev1_pdiag_asserted=dev1_pdiag_asserted,
            dev1_detection_method=dev1_detection_method,
            dev0_responds_when_dev1_selected=dev0_responds_when_dev1_selected,
            dev0_dasp_asserted=dev0_dasp_asserted,
            dev0_pdiag_asserted=dev0_pdiag_asserted,
            dev0_passed_diagnostics=dev0_passed_diagnostics,
            dev0_detection_method=dev0_detection_method,
        )


@dataclasses.dataclass(frozen=True)
class SectorSize:
    """Physical/logical sector size from word 106.

    Attributes:
        multiple_logical_per_physical: Multiple logical sectors per
            physical sector.
        logical_gt_256_words: Logical sector size greater than 256 words.
        relationship: Exponent of logical sectors per physical sector.

    """

    multiple_logical_per_physical: bool
    logical_gt_256_words: bool
    relationship: int

    @classmethod
    def parse(cls, word106: int) -> Self | None:
        """Parse physical/logical sector size.

        Args:
            word106: Raw word 106.

        Returns:
            Parsed physical/logical sector size if any.

        """
        if word106 >> 14 != 0b01:
            return None

        multiple_logical_per_physical: bool = bool(word106 & (1 << 13))
        logical_gt_256_words: bool = bool(word106 & (1 << 12))
        relationship: int = word106 & 0b1111

        return cls(
            multiple_logical_per_physical=multiple_logical_per_physical,
            logical_gt_256_words=logical_gt_256_words,
            relationship=relationship,
        )


class WWNNAA(enum.IntEnum):
    """Network Address Authority field of a World Wide Name.

    Attributes:
        IEEE: IEEE.
        IEEE_EXTENDED: IEEE Extended.
        IEEE_REGISTERED: IEEE Registered.

    """

    IEEE = 1
    IEEE_EXTENDED = 2
    IEEE_REGISTERED = 5


@dataclasses.dataclass(frozen=True)
class WWN:
    """World Wide Name.

    Attributes:
        naa: Network Address Authority type.
        oui: Organizationally Unique Identifier.
        vendor_specific: Vendor-specific identifier.

    """

    SIZE: ClassVar[int] = 8
    naa: WWNNAA
    oui: int
    vendor_specific: int

    def __bytes__(self) -> bytes:
        """Pack WWN into bytes.

        Returns:
            Bytes.

        Raises:
            ValueError: Invalid WWN.

        """
        value: int = self.naa << 60

        match self.naa:
            case WWNNAA.IEEE:
                value |= (self.oui << 24) | self.vendor_specific
            case WWNNAA.IEEE_EXTENDED:
                value |= (
                    (((self.vendor_specific >> 24) & 0xFFF) << 48)
                    | (self.oui << 24)
                    | (self.vendor_specific & 0xFFFFFF)
                )
            case WWNNAA.IEEE_REGISTERED:
                value |= (self.oui << 36) | self.vendor_specific
            case _:
                raise ValueError("Unsupported NAA", self.naa)

        return swap_word_bytes(value.to_bytes(8, "big"))

    @classmethod
    def parse(cls, data: bytes) -> Self:
        """Parse WWN.

        Args:
            data: Bytes.

        Returns:
            Parsed World Wide Name.

        Raises:
            ValueError: Invalid WWN.

        """
        if len(data) != cls.SIZE:
            raise ValueError("Invalid WWN size", len(data))

        value: int = int.from_bytes(swap_word_bytes(data), "big")
        naa: WWNNAA = WWNNAA((value >> 60) & 0xF)
        oui: int
        vendor_specific: int

        match naa:
            case WWNNAA.IEEE:
                oui = (value >> 24) & 0xFFFFFF
                vendor_specific = value & 0xFFFFFF
            case WWNNAA.IEEE_EXTENDED:
                oui = (value >> 24) & 0xFFFFFF
                vendor_specific = (((value >> 48) & 0xFFF) << 24) | (value & 0xFFFFFF)
            case WWNNAA.IEEE_REGISTERED:
                oui = (value >> 36) & 0xFFFFFF
                vendor_specific = value & 0xFFFFFFFFF
            case _:
                raise ValueError("Unsupported NAA", naa)

        return cls(naa=naa, oui=oui, vendor_specific=vendor_specific)


@dataclasses.dataclass(frozen=True)
class SecurityStatus:
    """Security status from word 128.

    Attributes:
        master_password_max: Master password capability is maximum.
        enhanced_security_erase: Enhanced security erase supported.
        security_count_expired: Security count expired.
        security_frozen: Security frozen.
        security_locked: Security locked.
        security_enabled: Security enabled.
        security_supported: Security feature set supported.

    """

    master_password_max: bool
    enhanced_security_erase: bool
    security_count_expired: bool
    security_frozen: bool
    security_locked: bool
    security_enabled: bool
    security_supported: bool

    @classmethod
    def parse(cls, word128: int) -> Self:
        """Parse security status.

        Args:
            word128: Raw word 128.

        Returns:
            Parsed security status.

        """
        master_password_max: bool = bool(word128 & (1 << 8))
        enhanced_security_erase: bool = bool(word128 & (1 << 5))
        security_count_expired: bool = bool(word128 & (1 << 4))
        security_frozen: bool = bool(word128 & (1 << 3))
        security_locked: bool = bool(word128 & (1 << 2))
        security_enabled: bool = bool(word128 & (1 << 1))
        security_supported: bool = bool(word128 & (1 << 0))

        return cls(
            master_password_max=master_password_max,
            enhanced_security_erase=enhanced_security_erase,
            security_count_expired=security_count_expired,
            security_frozen=security_frozen,
            security_locked=security_locked,
            security_enabled=security_enabled,
            security_supported=security_supported,
        )


@dataclasses.dataclass(frozen=True)
class CfaPowerMode:
    """CFA power mode from word 160.

    Attributes:
        level_1: CFA power level 1 commands supported.
        level_1_disable: CFA power level 1 is disabled.
        max_current: Maximum current in milliamps.

    """

    level_1: bool
    level_1_disable: bool
    max_current: int

    @classmethod
    def parse(cls, word160: int) -> Self | None:
        """Parse CFA power mode.

        Args:
            word160: Raw word 160.

        Returns:
            Parsed CFA power mode if any.

        """
        if not (word160 & (1 << 15)):
            return None

        level_1: bool = not bool(word160 & (1 << 13))
        level_1_disable: bool = bool(word160 & (1 << 12))
        max_current: int = word160 & 0xFFF

        return cls(
            level_1=level_1,
            level_1_disable=level_1_disable,
            max_current=max_current,
        )


class FormFactor(enum.IntEnum):
    """Nominal form factor from word 168.

    Attributes:
        INCH_5_25: 5.25 inch.
        INCH_3_5: 3.5 inch.
        INCH_2_5: 2.5 inch.
        INCH_1_8: 1.8 inch.
        INCH_LESS_THAN_1_8: Less than 1.8 inch.
        MSATA: mSATA.
        M_2: M.2.
        MICROSSD: MicroSSD.
        CFAST: CFast.

    """

    INCH_5_25 = 1
    INCH_3_5 = 2
    INCH_2_5 = 3
    INCH_1_8 = 4
    INCH_LESS_THAN_1_8 = 5
    MSATA = 6
    M_2 = 7
    MICROSSD = 8
    CFAST = 9

    @classmethod
    def parse(cls, word168: int) -> Self | None:
        """Parse form factor.

        Args:
            word168: Raw word 168.

        Returns:
            Parsed form factor if any.

        """
        raw: int = word168 & 0b1111
        return cls(raw) if raw else None


@dataclasses.dataclass(frozen=True)
class SCTSupported:
    """SMART Command Transport supported from word 206.

    Attributes:
        data_tables: SCT data tables.
        feature_control: SCT feature control.
        error_recovery_control: SCT error recovery control.
        write_same: SCT Write Same.
        sct: Smart Command Transport.

    """

    data_tables: bool
    feature_control: bool
    error_recovery_control: bool
    write_same: bool
    sct: bool

    @classmethod
    def parse(cls, word206: int) -> Self:
        """Parse SMART Command Transport supported.

        Args:
            word206: Raw word 206.

        Returns:
            Parsed SMART Command Transport supported.

        """
        data_tables: bool = bool(word206 & (1 << 5))
        feature_control: bool = bool(word206 & (1 << 4))
        error_recovery_control: bool = bool(word206 & (1 << 3))
        write_same: bool = bool(word206 & (1 << 2))
        sct: bool = bool(word206 & (1 << 0))

        return cls(
            data_tables=data_tables,
            feature_control=feature_control,
            error_recovery_control=error_recovery_control,
            write_same=write_same,
            sct=sct,
        )


class _TransportVersionMajorType(enum.IntEnum):
    """Transport type from word 222.

    Attributes:
        PARALLEL: Parallel.
        SERIAL: Serial.
        PCIE: PCIe.

    """

    PARALLEL = 0
    SERIAL = 1
    PCIE = 14


@dataclasses.dataclass(frozen=True)
class TransportVersionMajor:
    """Base transport major version from word 222."""

    @classmethod
    def parse(cls, word222: int) -> Self | None:
        """Parse transport major version.

        Args:
            word222: Raw word 222.

        Returns:
            Parsed transport major version if any.

        Raises:
            ValueError: Invalid transport type.

        """
        if word222 in (0, 0xFFFF):
            return None

        transport_type: _TransportVersionMajorType = _TransportVersionMajorType(
            word222 >> 12,
        )

        match transport_type:
            case _TransportVersionMajorType.PARALLEL:
                return TransportVersionMajorParallel.parse(word222)
            case _TransportVersionMajorType.SERIAL:
                return TransportVersionMajorSerial.parse(word222)
            case _TransportVersionMajorType.PCIE:
                return TransportVersionMajorPCIE()
            case x:
                raise ValueError("Invalid transport type", x)


@dataclasses.dataclass(frozen=True)
class TransportVersionMajorParallel(TransportVersionMajor):
    """Transport major version from word 222, Parallel type.

    Attributes:
        ata_atapi_7: ATA/ATAPI-7 supported.
        ata8_apt: ATA8-APT supported.

    """

    ata_atapi_7: bool
    ata8_apt: bool

    @classmethod
    @override
    def parse(cls, word222: int) -> Self:
        """Parse transport major version, Parallel type.

        Args:
            word222: Raw word 222.

        Returns:
            Parsed transport major version.

        """
        ata_atapi_7: bool = bool(word222 & (1 << 1))
        ata8_apt: bool = bool(word222 & (1 << 0))

        return cls(ata_atapi_7=ata_atapi_7, ata8_apt=ata8_apt)


@dataclasses.dataclass(frozen=True)
class TransportVersionMajorSerial(TransportVersionMajor):
    """Transport major version from word 222, serial type.

    Attributes:
        sata3_5: SATA 3.5 supported.
        sata3_4: SATA 3.4 supported.
        sata3_3: SATA 3.3 supported.
        sata3_2: SATA 3.2 supported.
        sata3_1: SATA 3.1 supported.
        sata3_0: SATA 3.0 supported.
        sata2_6: SATA 2.6 supported.
        sata2_5: SATA 2.5 supported.
        sata2_ext: SATA II Extensions supported.
        sata1_0a: SATA 1.0a supported.
        ata8_ast: ATA8-AST supported.

    """

    sata3_5: bool
    sata3_4: bool
    sata3_3: bool
    sata3_2: bool
    sata3_1: bool
    sata3_0: bool
    sata2_6: bool
    sata2_5: bool
    sata2_ext: bool
    sata1_0a: bool
    ata8_ast: bool

    @classmethod
    @override
    def parse(cls, word222: int) -> Self:
        """Parse transport major version.

        Args:
            word222: Raw word 222.

        Returns:
            Parsed transport major version.

        """
        sata3_5: bool = bool(word222 & (1 << 10))
        sata3_4: bool = bool(word222 & (1 << 9))
        sata3_3: bool = bool(word222 & (1 << 8))
        sata3_2: bool = bool(word222 & (1 << 7))
        sata3_1: bool = bool(word222 & (1 << 6))
        sata3_0: bool = bool(word222 & (1 << 5))
        sata2_6: bool = bool(word222 & (1 << 4))
        sata2_5: bool = bool(word222 & (1 << 3))
        sata2_ext: bool = bool(word222 & (1 << 2))
        sata1_0a: bool = bool(word222 & (1 << 1))
        ata8_ast: bool = bool(word222 & (1 << 0))

        return cls(
            sata3_5=sata3_5,
            sata3_4=sata3_4,
            sata3_3=sata3_3,
            sata3_2=sata3_2,
            sata3_1=sata3_1,
            sata3_0=sata3_0,
            sata2_6=sata2_6,
            sata2_5=sata2_5,
            sata2_ext=sata2_ext,
            sata1_0a=sata1_0a,
            ata8_ast=ata8_ast,
        )


@dataclasses.dataclass(frozen=True)
class TransportVersionMajorPCIE(TransportVersionMajor):
    """Transport major version from word 222, PCIE type."""


class TransportVersionMinor(enum.IntEnum):
    """Transport minor version number from word 223.

    Attributes:
        ATA8_AST_0B: ATA8-AST 0b.
        ATA8_AST_1: ATA8-AST 1.

    """

    ATA8_AST_0B = 0x21
    ATA8_AST_1 = 0x51

    @classmethod
    def parse(cls, word223: int) -> Self | None:
        """Parse transport minor version.

        Args:
            word223: Raw word 223.

        Returns:
            Parsed transport minor version if any.

        """
        return None if word223 in (0, 0xFFFF) else cls(word223)


def _parse_trusted_computing(trusted_comp_options: int) -> bool | None:
    if trusted_comp_options >> 14 != 0b01:
        return None

    return bool(trusted_comp_options & (1 << 0))


def _parse_queue_depth(raw: int) -> int:
    return (raw & 0b11111) + 1


def _parse_security_erase_time(raw: int) -> int | None:
    bit15: bool = bool(raw & (1 << 15))
    mask: int = 0b111111111111111 if bit15 else 0xFF
    time: int = (raw & mask) * 2

    return time or None


def _parse_master_password_id(word92: int) -> int | None:
    return None if word92 in (0, 0xFFFF) else word92


def _parse_logical_sector_size(raw: int, sector_size: SectorSize | None) -> int:
    gt_256_words: bool = sector_size is not None and sector_size.logical_gt_256_words
    logical_sector_size: int = raw * 2 if gt_256_words else command.SECTOR_SIZE

    if logical_sector_size < command.SECTOR_SIZE:
        raise ValueError("Invalid logical sector size", logical_sector_size)

    return logical_sector_size


def _parse_logical_sector_offset(logical_sector_align: int) -> int | None:
    valid: bool = logical_sector_align >> 14 == 0b01
    return logical_sector_align & 0b11111111111111 if valid else None


def _parse_rotation_rate(word217: int) -> int | None:
    match word217:
        case 0:
            return None
        case 1:
            return 0
        case x if 0x400 < x < 0xFFFF:
            return x

    raise ValueError("Invalid rotation rate", word217)


def _parse_dlmc_blocks(raw: int) -> int | None:
    if not (0 < raw < 0xFFFF):
        return None

    return raw


@dataclasses.dataclass(frozen=True)
class Identify:
    """ATA IDENTIFY DEVICE result.

    Attributes:
        SIZE: Size of IDENTIFY DEVICE data.
        general_config: General configuration.
        specific_config: Specific configuration.
        serial: Serial number.
        firmware: Firmware revision.
        model: Model.
        trusted_computing: Trusted Computing supported if any.
        capabilities: Device capabilities.
        freefall_sensitivity: Free-fall control sensitivity if any.
        sanitize_device_supported: Sanitize device supported.
        sector_count_28: Number of sectors 28-bit.
        multiword_dma_modes: Multiword DMA mode supported and selection.
        pio_modes: PIO mode supported if any.
        min_multiword_cycle_time: Minimum Multiword DMA transfer cycle
            time in nanoseconds if any.
        rec_multiword_cycle_time: Recommended Multiword DMA transfer
            cycle time in nanoseconds if any.
        min_pio_cycle_time: Minimum PIO transfer cycle time in nanoseconds if
            any.
        min_pio_cycle_time_iordy: Minimum PIO transfer cycle time with IORDY
            in nanoseconds if any.
        additional_supported: Additional supported capabilities if any.
        queue_depth: Maximum queue depth if any.
        sata_capabilities: SATA capabilities if any.
        sata_additional_capabilities: SATA additional capabilities if any.
        sata_features_supported: SATA features supported if any.
        sata_features_enabled: SATA features enabled if any.
        major_version: Major version number if any.
        minor_version: Minor version number if any.
        features_supported: Commands and feature sets supported.
        features_enabled: Commands and feature sets enabled.
        ultra_dma_modes: Ultra DMA mode supported and selection if any.
        security_erase_time: Security erase time in minutes if any.
        enhanced_security_erase_time: Enhanced security erase time in minutes
            if any.
        apm_level: Current Advanced Power Management level if any.
        master_password_id: Master Password identifier if any.
        hardware_reset: Hardware reset result if any.
        stream_min_req_size: Minimum request size for streaming if any.
        stream_transfer_time_dma: Streaming DMA transfer time if any.
        stream_access_latency: Streaming DMA access latency if any.
        stream_perf_granularity: Streaming performance granularity if any.
        sector_count_48: Number of sectors 48-bit if any.
        stream_transfer_time_pio: Streaming PIO transfer time if any.
        max_blocks_per_trim: Maximum number of blocks per TRIM command.
        sector_size: Physical/logical sector size information if any.
        interseek_delay: Inter-seek delay for acoustic management.
        wwn: World Wide Name if any.
        logical_sector_size: Logical sector size.
        security_status: Security status if any.
        vendor_specific: Vendor-specific data.
        cfa_power_mode: CFA power mode if any.
        form_factor: Nominal form factor if any.
        trim_supported: TRIM supported.
        additional_product_id: Additional product identifier if any.
        media_serial: Media serial number if any.
        sct: SCT supported.
        logical_sector_offset: Logical sector offset if any.
        wrv_mode3_count: Count of mode 3 sectors for Write-Read-Verify if any.
        wrv_mode2_count: Count of mode 2 sectors for Write-Read-Verify if any.
        rotation_rate: Nominal media rotation rate if any.
        wrv_current_mode: Current Write-Read-Verify mode if any.
        transport_version_major: Transport major version if any.
        transport_version_minor: Transport minor version if any.
        sector_count_ext: Extended number of sectors if any.
        dlmc_min_blocks: Minimum number of DOWNLOAD MICROCODE blocks if any.
        dlmc_max_blocks: Maximum number of DOWNLOAD MICROCODE blocks if any.

    """

    _STRUCT: ClassVar[struct.Struct] = struct.Struct(
        "<H"
        "2x"
        "H"
        "14x"
        "20s"
        "6x"
        "8s"
        "40s"
        "2x"
        "3H"
        "4x"
        "H"
        "10x"
        "H"
        "L"
        "2x"
        "7H"
        "10x"
        "16H"
        "B"
        "x"
        "2H"
        "2x"
        "3H"
        "L"
        "Q"
        "4H"
        "8s"
        "10x"
        "L"
        "2H"
        "14x"
        "H"
        "62s"
        "H"
        "14x"
        "2H"
        "8s"
        "4x"
        "60s"
        "H"
        "4x"
        "H"
        "2L"
        "6x"
        "H"
        "4x"
        "B"
        "3x"
        "2H"
        "12x"
        "Q"
        "2H"
        "40x",
    )
    SIZE: ClassVar[int] = _STRUCT.size

    general_config: GeneralConfig
    specific_config: int
    serial: str
    firmware: str
    model: str
    trusted_computing: bool | None
    capabilities: Capabilities
    freefall_sensitivity: int | None
    sanitize_device_supported: SanitizeSupported
    sector_count_28: int
    multiword_dma_modes: MultiwordDMAModes
    pio_modes: PIOModes | None
    min_multiword_cycle_time: int | None
    rec_multiword_cycle_time: int | None
    min_pio_cycle_time: int | None
    min_pio_cycle_time_iordy: int | None
    additional_supported: AdditionalSupported | None
    queue_depth: int | None
    sata_capabilities: SataCapabilities | None
    sata_additional_capabilities: SataAdditionalCapabilities | None
    sata_features_supported: SataFeaturesSupported | None
    sata_features_enabled: SataFeaturesEnabled | None
    major_version: MajorVersion | None
    minor_version: MinorVersion | None
    features_supported: FeaturesSupported
    features_enabled: FeaturesEnabled
    ultra_dma_modes: UltraDMAModes | None
    security_erase_time: int | None
    enhanced_security_erase_time: int | None
    apm_level: int | None
    master_password_id: int | None
    hardware_reset: HardwareResetResult | None
    stream_min_req_size: int | None
    stream_transfer_time_dma: int | None
    stream_access_latency: int | None
    stream_perf_granularity: int | None
    sector_count_48: int | None
    stream_transfer_time_pio: int | None
    max_blocks_per_trim: int
    sector_size: SectorSize | None
    interseek_delay: int
    wwn: WWN | None
    logical_sector_size: int
    security_status: SecurityStatus | None
    vendor_specific: bytes
    cfa_power_mode: CfaPowerMode | None
    form_factor: FormFactor | None
    trim_supported: bool
    additional_product_id: str | None
    media_serial: str | None
    sct: SCTSupported
    logical_sector_offset: int | None
    wrv_mode3_count: int | None
    wrv_mode2_count: int | None
    rotation_rate: int | None
    wrv_current_mode: int | None
    transport_version_major: TransportVersionMajor | None
    transport_version_minor: TransportVersionMinor | None
    sector_count_ext: int | None
    dlmc_min_blocks: int | None
    dlmc_max_blocks: int | None

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Parse IDENTIFY DEVICE from bytes.

        Args:
            data: Bytes.

        Returns:
            Parsed IDENTIFY DEVICE.

        Raises:
            ValueError: Invalid data.

        """
        general_config_raw: int
        specific_config: int
        serial_raw: bytes
        firmware_raw: bytes
        model_raw: bytes
        trusted_comp_options: int
        capabilities_word1: int
        capabilities_word2: int
        word_53: int
        sanitize_device_supported_raw: int
        sector_count_28: int
        multiword_dma_modes_raw: int
        pio_modes_raw: int
        min_multiword_cycle_time_raw: int
        rec_multiword_cycle_time_raw: int
        min_pio_cycle_time_raw: int
        min_pio_cycle_time_iordy_raw: int
        additional_supported_raw: int
        queue_depth_raw: int
        sata_capabilities_raw: int
        sata_additional_capabilities_raw: int
        sata_features_supported_raw: int
        sata_features_enabled_raw: int
        major_version_raw: int
        minor_version_raw: int
        features_supported_word1: int
        features_supported_word2: int
        features_supported_word3: int
        features_enabled_word1: int
        features_enabled_word2: int
        features_enabled_word3: int
        ultra_dma_modes_raw: int
        security_erase_time_raw: int
        enhanced_security_erase_time_raw: int
        apm_level_raw: int
        master_password_id_raw: int
        hardware_reset_raw: int
        stream_min_req_size_raw: int
        stream_transfer_time_dma_raw: int
        stream_access_latency_raw: int
        stream_perf_granularity_raw: int
        sector_count_48_raw: int
        stream_transfer_time_pio_raw: int
        max_blocks_per_trim: int
        sector_size_raw: int
        interseek_delay: int
        wwn_raw: bytes
        logical_sector_size_raw: int
        features_supported_word4: int
        features_enabled_word4: int
        security_status_raw: int
        vendor_specific: bytes
        cfa_power_mode_raw: int
        form_factor_raw: int
        trim_supported_raw: int
        additional_product_id_raw: bytes
        media_serial_raw: bytes
        sct_raw: int
        logical_sector_align: int
        wrv_mode3_count_raw: int
        wrv_mode2_count_raw: int
        rotation_rate_raw: int
        wrv_current_mode_raw: int
        transport_version_major_raw: int
        transport_version_minor_raw: int
        sector_count_ext_raw: int
        dlmc_min_blocks_raw: int
        dlmc_max_blocks_raw: int
        (
            general_config_raw,
            specific_config,
            serial_raw,
            firmware_raw,
            model_raw,
            trusted_comp_options,
            capabilities_word1,
            capabilities_word2,
            word_53,
            sanitize_device_supported_raw,
            sector_count_28,
            multiword_dma_modes_raw,
            pio_modes_raw,
            min_multiword_cycle_time_raw,
            rec_multiword_cycle_time_raw,
            min_pio_cycle_time_raw,
            min_pio_cycle_time_iordy_raw,
            additional_supported_raw,
            queue_depth_raw,
            sata_capabilities_raw,
            sata_additional_capabilities_raw,
            sata_features_supported_raw,
            sata_features_enabled_raw,
            major_version_raw,
            minor_version_raw,
            features_supported_word1,
            features_supported_word2,
            features_supported_word3,
            features_enabled_word1,
            features_enabled_word2,
            features_enabled_word3,
            ultra_dma_modes_raw,
            security_erase_time_raw,
            enhanced_security_erase_time_raw,
            apm_level_raw,
            master_password_id_raw,
            hardware_reset_raw,
            stream_min_req_size_raw,
            stream_transfer_time_dma_raw,
            stream_access_latency_raw,
            stream_perf_granularity_raw,
            sector_count_48_raw,
            stream_transfer_time_pio_raw,
            max_blocks_per_trim,
            sector_size_raw,
            interseek_delay,
            wwn_raw,
            logical_sector_size_raw,
            features_supported_word4,
            features_enabled_word4,
            security_status_raw,
            vendor_specific,
            cfa_power_mode_raw,
            form_factor_raw,
            trim_supported_raw,
            additional_product_id_raw,
            media_serial_raw,
            sct_raw,
            logical_sector_align,
            wrv_mode3_count_raw,
            wrv_mode2_count_raw,
            rotation_rate_raw,
            wrv_current_mode_raw,
            transport_version_major_raw,
            transport_version_minor_raw,
            sector_count_ext_raw,
            dlmc_min_blocks_raw,
            dlmc_max_blocks_raw,
        ) = cls._STRUCT.unpack(data)

        general_config: GeneralConfig = GeneralConfig.parse(general_config_raw)

        serial: str
        firmware: str
        model: str
        serial, firmware, model = map(
            decode_string,
            (serial_raw, firmware_raw, model_raw),
        )

        trusted_computing: bool | None = _parse_trusted_computing(trusted_comp_options)

        capabilities: Capabilities = Capabilities.parse(
            capabilities_word1,
            capabilities_word2,
        )

        features_enabled: FeaturesEnabled = FeaturesEnabled.parse(
            features_enabled_word1,
            features_enabled_word2,
            features_enabled_word3,
            features_enabled_word4,
        )

        features_supported: FeaturesSupported = FeaturesSupported.parse(
            features_supported_word1,
            features_supported_word2,
            features_supported_word3,
            (
                features_supported_word4
                if features_enabled.words_119_120_valid
                else None
            ),
        )

        freefall_sensitivity: int | None = (
            word_53 >> 8
            if features_supported.freefall_control and features_enabled.freefall_control
            else None
        )

        ultra_dma_modes_valid: bool = bool(word_53 & (1 << 2))
        words_64_to_70_valid: bool = bool(word_53 & (1 << 1))

        sanitize_device_supported: SanitizeSupported = SanitizeSupported.parse(
            sanitize_device_supported_raw,
        )

        multiword_dma_modes: MultiwordDMAModes = MultiwordDMAModes.parse(
            multiword_dma_modes_raw,
        )

        pio_modes: PIOModes | None = (
            PIOModes.parse(pio_modes_raw) if words_64_to_70_valid else None
        )

        min_multiword_cycle_time: int | None = (
            min_multiword_cycle_time_raw if words_64_to_70_valid else None
        )

        rec_multiword_cycle_time: int | None = (
            rec_multiword_cycle_time_raw if words_64_to_70_valid else None
        )

        min_pio_cycle_time: int | None = (
            min_pio_cycle_time_raw if words_64_to_70_valid else None
        )

        min_pio_cycle_time_iordy: int | None = (
            min_pio_cycle_time_iordy_raw if words_64_to_70_valid else None
        )

        additional_supported: AdditionalSupported | None = (
            AdditionalSupported.parse(additional_supported_raw)
            if words_64_to_70_valid
            else None
        )

        sata_capabilities: SataCapabilities | None = SataCapabilities.parse(
            sata_capabilities_raw,
        )

        queue_depth: int | None = (
            _parse_queue_depth(queue_depth_raw)
            if sata_capabilities and sata_capabilities.ncq
            else None
        )

        sata_valid: bool = sata_capabilities is not None

        sata_additional_capabilities: SataAdditionalCapabilities | None = (
            SataAdditionalCapabilities.parse(
                sata_additional_capabilities_raw,
            )
            if sata_valid
            else None
        )

        sata_features_supported: SataFeaturesSupported | None = (
            SataFeaturesSupported.parse(
                sata_features_supported_raw,
            )
            if sata_valid
            else None
        )

        sata_features_enabled: SataFeaturesEnabled | None = (
            SataFeaturesEnabled.parse(
                sata_features_enabled_raw,
            )
            if sata_valid
            else None
        )

        major_version: MajorVersion | None = MajorVersion.parse(major_version_raw)
        minor_version: MinorVersion | None = MinorVersion.parse(minor_version_raw)

        ultra_dma_modes: UltraDMAModes | None = (
            UltraDMAModes.parse(ultra_dma_modes_raw) if ultra_dma_modes_valid else None
        )

        security_erase_time: int | None = _parse_security_erase_time(
            security_erase_time_raw,
        )

        enhanced_security_erase_time: int | None = _parse_security_erase_time(
            enhanced_security_erase_time_raw,
        )

        apm_level: int | None = (
            apm_level_raw if features_supported.apm and features_enabled.apm else None
        )

        master_password_id: int | None = _parse_master_password_id(
            master_password_id_raw,
        )

        hardware_reset: HardwareResetResult | None = HardwareResetResult.parse(
            hardware_reset_raw,
        )

        security_status: SecurityStatus | None = (
            SecurityStatus.parse(security_status_raw)
            if features_supported.security
            else None
        )

        streaming_valid: bool = bool(features_supported.streaming)

        stream_min_req_size: int | None = (
            stream_min_req_size_raw if streaming_valid else None
        )

        stream_transfer_time_dma: int | None = (
            stream_transfer_time_dma_raw if streaming_valid else None
        )

        stream_access_latency: int | None = (
            stream_access_latency_raw if streaming_valid else None
        )

        stream_perf_granularity: int | None = (
            stream_perf_granularity_raw if streaming_valid else None
        )

        sector_count_48: int | None = (
            sector_count_48_raw if features_supported.address_48bit else None
        )

        stream_transfer_time_pio: int | None = (
            stream_transfer_time_pio_raw if streaming_valid else None
        )

        sector_size: SectorSize | None = SectorSize.parse(
            sector_size_raw,
        )

        logical_sector_size: int = _parse_logical_sector_size(
            logical_sector_size_raw,
            sector_size,
        )

        logical_sector_offset: int | None = (
            _parse_logical_sector_offset(logical_sector_align)
            if sector_size and sector_size.multiple_logical_per_physical
            else None
        )

        wwn: WWN | None = (
            WWN.parse(wwn_raw)
            if bool(features_supported.wwn)
            and bool(features_enabled.wwn)
            and any(wwn_raw)
            else None
        )

        cfa_power_mode: CfaPowerMode | None = CfaPowerMode.parse(cfa_power_mode_raw)
        form_factor: FormFactor | None = FormFactor.parse(form_factor_raw)
        trim_supported: bool = bool(trim_supported_raw & (1 << 0))

        additional_product_id: str | None = (
            decode_string(additional_product_id_raw)
            if any(additional_product_id_raw)
            else None
        )

        media_serial: str | None = (
            decode_string(media_serial_raw)
            if features_enabled.media_serial_valid
            else None
        )

        sct: SCTSupported = SCTSupported.parse(sct_raw)
        wrv_valid: bool = bool(features_supported.wrv) and bool(features_enabled.wrv)
        wrv_current_mode: int | None = wrv_current_mode_raw if wrv_valid else None

        wrv_mode3_count: int | None = (
            wrv_mode3_count_raw if wrv_valid and wrv_current_mode == 3 else None
        )

        wrv_mode2_count: int | None = wrv_mode2_count_raw if wrv_valid else None
        rotation_rate: int | None = _parse_rotation_rate(rotation_rate_raw)

        transport_version_major: TransportVersionMajor | None = (
            TransportVersionMajor.parse(
                transport_version_major_raw,
            )
        )

        transport_version_minor: TransportVersionMinor | None = (
            TransportVersionMinor.parse(
                transport_version_minor_raw,
            )
        )

        sector_count_ext: int | None = (
            sector_count_ext_raw
            if (additional_supported and additional_supported.sector_count_ext)
            else None
        )

        dlmc_blocks_valid: bool = (
            features_supported.dlmc
            or (additional_supported is not None and additional_supported.dlmc_dma)
        ) and bool(features_supported.dlmc_mode3)

        dlmc_min_blocks: int | None = (
            _parse_dlmc_blocks(dlmc_min_blocks_raw) if dlmc_blocks_valid else None
        )

        dlmc_max_blocks: int | None = (
            _parse_dlmc_blocks(dlmc_max_blocks_raw) if dlmc_blocks_valid else None
        )

        return cls(
            general_config=general_config,
            specific_config=specific_config,
            serial=serial,
            firmware=firmware,
            model=model,
            trusted_computing=trusted_computing,
            capabilities=capabilities,
            freefall_sensitivity=freefall_sensitivity,
            sanitize_device_supported=sanitize_device_supported,
            sector_count_28=sector_count_28,
            multiword_dma_modes=multiword_dma_modes,
            pio_modes=pio_modes,
            min_multiword_cycle_time=min_multiword_cycle_time,
            rec_multiword_cycle_time=rec_multiword_cycle_time,
            min_pio_cycle_time=min_pio_cycle_time,
            min_pio_cycle_time_iordy=min_pio_cycle_time_iordy,
            additional_supported=additional_supported,
            queue_depth=queue_depth,
            sata_capabilities=sata_capabilities,
            sata_additional_capabilities=sata_additional_capabilities,
            sata_features_supported=sata_features_supported,
            sata_features_enabled=sata_features_enabled,
            major_version=major_version,
            minor_version=minor_version,
            features_supported=features_supported,
            features_enabled=features_enabled,
            ultra_dma_modes=ultra_dma_modes,
            security_erase_time=security_erase_time,
            enhanced_security_erase_time=enhanced_security_erase_time,
            apm_level=apm_level,
            master_password_id=master_password_id,
            hardware_reset=hardware_reset,
            stream_min_req_size=stream_min_req_size,
            stream_transfer_time_dma=stream_transfer_time_dma,
            stream_access_latency=stream_access_latency,
            stream_perf_granularity=stream_perf_granularity,
            sector_count_48=sector_count_48,
            stream_transfer_time_pio=stream_transfer_time_pio,
            max_blocks_per_trim=max_blocks_per_trim,
            sector_size=sector_size,
            interseek_delay=interseek_delay,
            wwn=wwn,
            logical_sector_size=logical_sector_size,
            security_status=security_status,
            vendor_specific=vendor_specific,
            cfa_power_mode=cfa_power_mode,
            form_factor=form_factor,
            trim_supported=trim_supported,
            additional_product_id=additional_product_id,
            media_serial=media_serial,
            sct=sct,
            logical_sector_offset=logical_sector_offset,
            wrv_mode3_count=wrv_mode3_count,
            wrv_mode2_count=wrv_mode2_count,
            rotation_rate=rotation_rate,
            wrv_current_mode=wrv_current_mode,
            transport_version_major=transport_version_major,
            transport_version_minor=transport_version_minor,
            sector_count_ext=sector_count_ext,
            dlmc_min_blocks=dlmc_min_blocks,
            dlmc_max_blocks=dlmc_max_blocks,
        )
