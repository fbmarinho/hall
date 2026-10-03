import socket
import struct

HOST = '127.0.0.1'
PORT = 23052

commands = [
    # --- Comandos de Sistema e Configuração (0x10xx) ---
    0x1001,  # CMD_SHUTDOWN
    0x1002,  # CMD_HANDSHAKE
    0x100c,  # CMD_DELETE_DATASET
    0x100d,  # CMD_RENAME_DATASET
    0x100e,  # CMD_COPY_DATASET
    0x1016,  # CMD_QUERY_SERVER_STATS
    0x1017,  # CMD_IDENTIFY_2
    0x101c,  # CMD_QUERY_ACTIVE_CONNECTIONS
    0x101f,  # CMD_IDENTIFY

    # --- Comandos de Consulta Geral e Metadados (0x20xx) ---
    0x2001,  # CMD_QUERY_VARIABLE
    0x2003,  # CMD_QUERY_UNIT_TYPES
    0x2004,  # CMD_QUERY_UNIT_TYPE_NAME
    0x2005,  # CMD_QUERY_UNIT_TYPE_BY_NAME
    0x2006,  # CMD_QUERY_UNIT_OPTIONS_BY_TYPE_SHORT_LONG
    0x2007,  # CMD_QUERY_UNIT_CONVERSION_INFO
    0x2009,  # CMD_QUERY_OPTIONS_LISTS
    0x200d,  # CMD_QUERY_WELL_LIST
    0x2010,  # CMD_QUERY_DATASET_EXISTS
    0x2012,  # CMD_QUERY_RUN_RECORD_VARIABLES
    0x2013,  # CMD_QUERY_RECORD_VARIABLES
    0x2014,  # CMD_QUERY_STATISTICS_OPERATIONS
    0x2015,  # CMD_QUERY_RECORD_ATTRIBUTES
    0x2017,  # CMD_QUERY_UNITSET_NAMES
    0x2018,  # CMD_LOAD_UNITSET
    0x2019,  # CMD_QUERY_VARIABLE_DECIMALS_PER_OPTION
    0x2020,  # CMD_QUERY_STRING_VALUE
    0x2021,  # CMD_QUERY_INT_VALUE
    0x2022,  # CMD_QUERY_DOUBLE_VALUE
    0x203e,  # CMD_QUERY_RUN_NUMBER
    0x2043,  # CMD_QUERY_DATASETS
    0x2044,  # CMD_QUERY_NUMBER_DATASETS
    0x2045,  # CMD_UNKNOWN_02
    0x2049,  # CMD_QUERY_UDNOTIBYNAME
    0x2051,  # CMD_QUERY_RECORDS_BY_PSL_TYPES
    0x2052,  # CMD_QUERY_RECORD_LIST
    0x205a,  # CMD_QUERY_RECORD_ATTRIBUTES_XML
    0x205e,  # CMD_QUERY_VARS_INFO
    0x2065,  # CMD_QUERY_UNIT_TYPES_OPTIONS
    0x2066,  # CMD_QUERY_UNIT_TYPE_OPTIONS
    0x206d,  # CMD_QUERY_VARIABLES_DECIMALS_PER_OPTION
    0x2071,  # CMD_QUERY_UNITSET
    0x2072,  # CMD_QUERY_RUN_LIST

    # --- Comandos de Definições (0x30xx) ---
    0x3011,  # CMD_QUERY_TABLE_DEFINITIONS

    # --- Comandos de Manipulação de Datasets (0x90xx) ---
    0x9000,  # ADI_DATASET_PREPARE
    0x9001,  # ADI_DATASET_CLOSE
    0x9002,  # ADI_DATASET_OPEN
    0x9004,  # ADI_DATASET_OPEN_COMPLEX
    0x9007,  # ADI_DATASET_WRITE_BAG_DATA
    0x9008,  # ADI_DATASET_READ_BAG_DATA
    0x900a,  # ADI_DATASET_WRITE
    0x900b,  # ADI_DATASET_READ
    0x900c,  # ADI_DATASET_SET_INDEX_POSITION
    0x900d,  # ADI_DATASET_DELETE_SINGLE_LINE_BY_INDEX_POSITION
    0x900e,  # ADI_DATASET_WRITE_2
    0x9010,  # ADI_DATASET_READ_MULTIPLE
    0x9011,  # ADI_DATASET_UPDATE_BY_INDEX_POSITION
    0x9012,  # ADI_DATASET_DELETE_BY_INDEX_POSITION
    0x9013,  # ADI_DATASET_QUERY_NUM_RECORDS
    0x9014,  # ADI_DATASET_SET_UNKNOWN_TIME_3
    0x9015,  # ADI_DATASET_SET_UNKNOWN
    0x9016,  # ADI_DATASET_SET_INDEX_TYPE
    0x901b,  # ADI_DATASET_CLEAR
    0x901c,  # ADI_DATASET_LOOKUP
    0x901d,  # ADI_DATASET_READ_COMMENTS
    0x901f,  # ADI_DATASET_APPEND_COMMENTS
    0x9021,  # ADI_DATASET_READ_NEXT
    0x9022,  # ADI_DATASET_READ_WITH_LIMIT
    0x9024,  # ADI_DATASET_GET_CURRENT_POSITION
    0x9026,  # ADI_DATASET_WRITE_MULTIPLE
    0x9029,  # ADI_DATASET_LIST_BAG_DATA_FIELDS
    0x902a,  # ADI_DATASET_READ_OVER_RANGE
    0x902e,  # ADI_DATASET_OPEN_RT_BROADCAST
    0x9030,  # ADI_DATASET_READ_FILE
    0x9032,  # ADI_DATASET_GET_FILES_LIST
    0x9034,  # ADI_DATASET_SET_TDA_FILTER
    0x9036,  # ADI_DATASET_SET_UNKNOWN_TIME_4
    0x9037,  # ADI_DATASET_SEARCH_SMOOTH
    0x9039,  # ADI_DATASET_GET_MIN_MAX_INDEX
    0x903d,  # ADI_DATASET_WRITE_VECTOR_ATTRIBUTES
    0x903e,  # ADI_DATASET_READ_VECTOR_ATTRIBUTES

    # --- Comandos de Tempo Real (0xA0xx) ---
    0xa003,  # CMD_RT_DATASET_MONITOR
    0xa006,  # CMD_RT_STOP
    0xa007,  # CMD_RT_STOP_ALL
    0xa008,  # CMD_RT_UNKNOWN_a008
    0xa009,  # CMD_CHECK_RT_SMT
    0xa00e,  # CMD_RT_UNKNOWN_a00e
    0xa010,  # CMD_RT_CHECK_KEY
    0xa011,  # CMD_RT_DISCONNECT_KEY
    0xa012,  # CMD_RT_SUBSCRIBE_EVENT
    0xa018,  # CMD_RT_START
    0xa064,  # CMD_RT_MESSAGE
    0xa066,  # CMD_RT_EVENT

    # --- Comandos de Segurança e Diversos (0xC0xx) ---
    0xc022,  # CMD_UNKNOWN_01
    0xc02d,  # CMD_PASSWORD_CHANGE

    # --- Comandos de Troca de Dados / DEX (0xD0xx) ---
    0xd001,  # CMD_DEX_ADD
    0xd002,  # CMD_DEX_REMOVE
    0xd003,  # CMD_DEX_LIST
    0xd00b,  # CMD_DEX_SET_DESCRIPTION

    # --- Outros Comandos (0xE0xx) ---
    0xe004,  # CMD_QUERY_DATA_DICTIONARIES
]


def connect(command):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5)
        
        print(f"[*] Conectando a {HOST}:{PORT}...")
        client.connect((HOST, PORT))
        print("[+] Conectado com sucesso!\n")
        
        # ====================================================================
        # PASSO 1: Enviando commando
        # ====================================================================
        
        protocol = 0x65
        format = 0
        param = 0
        length = 0

        bytes_data = struct.pack("<hhIII", protocol, format, command, param, length)
        client.sendall(bytes_data)
        
        response = client.recv(4096)

        if len(response) < 16:
            print("[-] Erro: Resposta muito curta recebida do servidor.")
            return

        header_format = "<hhIII"
        header_size = struct.calcsize(header_format)

        protocol_resp, format_resp, param_resp, value_resp, length_resp = struct.unpack(header_format, response[:16])

        print(f"\n[<] Cabeçalho Recebido:")
        print(f"    - Protocolo : {protocol_resp}")
        print(f"    - Formato   : {format_resp}")
        print(f"    - Parâmetro : {param_resp}")
        print(f"    - Valor     : {value_resp}")
        print(f"    - Comprimento do Payload: {length_resp} bytes\n")

        payload_data = response[header_size:]

        print(f"[*] Payload Recebido: {payload_data}\n")

            
    except Exception as e:
        print(f"\n[-] Erro na conexão: {e}")
    finally:
        client.close()
        print("\n[*] Conexão encerrada.")

if __name__ == '__main__':
    for command in commands:
        print(f"\n==============================\nTestando comando: {hex(command)}\n==============================")
        connect(command)
