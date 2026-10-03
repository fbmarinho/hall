from __future__ import annotations
from enum import Enum, IntFlag


class ConnectionState(Enum):
    CLOSED = 1
    CONNECTING = 2
    INITIALIZING = 3
    CONNECTED = 4
    CLOSING = 5


class ClientState(Enum):
    INITIALIZING = 1
    IDLE = 2
    RECEIVING = 3
    IDENTIFYING_MSG = 4
    PROCESSING = 5
    BUILDING_RESPONSE = 6
    SENDING = 7


class BlockReadOption(Enum):
    OnePointPast = 0
    LessOrEqual = 1
    GreaterOrEqual = 2
    OneIndexPast = 3


class CoercionTypes(Enum):
    IndependentVariable = 0xffffffff
    NoCoercion = 0
    Max = 1
    Min = 2
    Mean = 3
    StandardDeviation = 4
    Smooth = 5
    Last = 6
    Next = 7
    LastInInterval = 8
    MeanWindow = 9
    Near = 10
    LinearInterpolation = 11


class IdentificationState(Enum):
    INITIALIZING = 1
    SENDING_CREDENTIALS = 2
    AUTHENTICATING = 3
    COMPLETE = 7


class QueryValueType(Enum):
    BitDepth = 0
    HoleDepth = 1
    WellId = 2
    RunNumber = 3
    SideTrack = 4
    TimeDepthActivity = 5
    DrillModelDescriptor = 6
    LithologyDescriptor = 7
    SurveyDescriptor = 8
    FormationTops = 9
    WellKillState = 10
    PeZiState = 11
    LockTolerance = 12
    LockRetryPeriod = 13
    ValueTypeMax = 14


class VarType(Enum):
    ADI_VT_NONE = 0
    ADI_VT_CHAR = 1
    ADI_VT_UCHAR = 2
    ADI_VT_SHORT = 3
    ADI_VT_USHORT = 4
    ADI_VT_INT = 5
    ADI_VT_LONG = 5
    ADI_VT_UINT = 6
    ADI_VT_ULONG = 6
    ADI_VT_FLOAT = 7
    ADI_VT_DOUBLE = 8
    ADI_VT_STRING = 9
    ADI_VT_PCHAR = 10
    ADI_VT_BINARY = 11
    ADI_VT_PBYTE = 12
    ADI_VT_ENUM = 13


class VectorVarType(Enum):
    Unknown = 0
    UnsignedByteId = 1
    UnsignedShortId = 2
    UnsignedIntId = 3
    ByteId = 4
    ShortId = 5
    IntId = 6
    FloatId = 7
    DoubleId = 8


class StorageType(Enum):
    NUMBER = 1
    NUMBER_UNSIGNED = 2
    NUMBER_DECIMAL = 3
    TEXT = 4
    TEXT_LONG = 5
    BINARY = 6
    BINARY_LONG = 7
    I1_ARRAY = 101
    I2_ARRAY = 102
    I4_ARRAY = 103
    U1_ARRAY = 104
    U2_ARRAY = 105
    U4_ARRAY = 106
    F4_ARRAY = 107
    F8_ARRAY = 108


class VariableSpecialHandlings(Enum):
    Nothing = 0
    Calculable = 1
    OptionList = 2
    DerivedDepth = 4
    DateFormat = 8
    WaveForm = 16
    EnumList = 32
    BoundArray = 64
    VectorData = 256


class QueryFilterModes(IntFlag):
    WELL = 0x04
    RUN_ALIAS = 0x02
    RUN_NUMBER = 0x01
    RECORD = 0x10
    DESCRIPTION = 0x08


class OutputFormat(IntFlag):
    DEFAULT = 0
    BINARY_SIMPLE = 1
    BINARY_FULL = 2
    XML_SIMPLE = 3
    XML_FULL = 4
    JSON = 9

    
class RecordOpenModes(IntFlag):
    ModeNone = 0
    Read = 1
    Write = 2
    Create = 4
    NoTruncate = 8
    DepthIndex = 16
    TimeIndex = 32
    DeferSecondIndex = 64
    SaveBackup = 128
    Shared = 256
    RealTimeAppend = 512
    ExactRecord = 1024
    PostRealTimeData = 2048
    DeferPrimaryIndex = 4096
    ReadWrite = 3
    Read2 = 256
    Write2 = 256
    DescriptorMode = 8192


class IndexType(Enum):
    Sequential = 0x01   # Maybe 0x00 ? :(
    Time = 0x02
    Depth = 0x04
    Activity = 0x08
    Free = 0x8000

    
class RecordOpenModesInsite(Enum):
    DefaultRead = 0
    Read = 1
    Write = 2
    Create = 4
    NoTruncate = 8
    DepthIndex = 0x10
    TimeIndex = 0x20
    DeferSecondIndex = 0x40
    SaveBackup = 0x80
    Shared = 0x100
    RealTimeAppend = 0x200
    ExactRecord = 0x400
    PostRealTimeData = 0x800
    DeferPrimaryIndex = 0x1000
    ReadWrite = 3
    Read2 = 0x100
    Write2 = 0x100
    DescriptorMode = 0x2000
    
    
class SeekPositionMode(Enum):
    Start = 0x00
    End = 0x01
    RecordNumber = 0x02
    Time = 0x03
    Depth = 0x04


class SearchDirection(Enum):
    Up = 0x00
    Down = 0x01


class RecordPrimaryKeys(Enum):
    Well = 1
    BitRun = 2
    Description = 4


class RecordAttributes(Enum):
    Hidden = 1
    ReadOnly = 2
    Locked = 4


class DataSetWriteModes(IntFlag):
    Overwrite = 0
    Insert = 1
    Exclusive = 2
    StoreData = 4
    PostRealTimeData = 8
    Update = 0x10
    UpdateExact = 0x20
    UserUtcTime = 0x40
    Compressed = 0x80


class DataTransferAdiType(Enum):
    InsiteAdi = 1
    LocalAdi = 2


class DataTransferDatasetsType(Enum):
    FullDatabase = 1
    ActiveWell = 2
    ActiveRun = 3
    ActivePass = 4
    SelectedDatasets = 5


class DataTransferDirection(Enum):
    ReceiveFrom = 0
    SendTo = 1


class DataTransferRtStoredType(Enum):
    RealtimeOnly = 1
    StoredOnly = 2
    RealtimeAndStored = 3


class DataTransferMode(Enum):
    Continuous = 1
    OneTimeNow = 2
    OneTimeAtTime = 3
    OneTimeAtDepth = 4
    PeriodicAtTime = 5
    PeriodicAtDepth = 6


class DataTransferConnectionStatus(Enum):
    Disabled = 1
    Connecting = 2
    Connected = 3


class DataTransferStatus(Enum):
    Stopped = 1
    AttemptingConnection = 2
    ListingDatasets = 3
    TransferringData = 4
