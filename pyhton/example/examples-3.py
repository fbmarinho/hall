from adi import AdiClientToRemote
from adi import AdiCommands
from adi import AdiDefinitions
from adi import AdiEnums
import asyncio
import datetime
import json
import sys


k1 = AdiDefinitions.AdiDataSetPrimaryKey(well="35_6-5S", run_number=400, record="DGR", description="Realtime")
iv = AdiDefinitions.AdiVariable(name="Depth", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=3)))

async def example1():
    adi_client:AdiClientToRemote.AdiClientToRemote = AdiClientToRemote.AdiClientToRemote(asyncio.get_event_loop(), host="11.11.0.102", enabled=True, realtime=False)
    while adi_client.connection_state != AdiDefinitions.ConnectionState.CONNECTED: await asyncio.sleep(0.1)

    ds = await adi_client.OpenDataSet(record="Download", description="Detection", bag_mode=True)
    files = await ds.GetFilesList()
    data = await ds.ReadFile(files[0]['EntryName'])
    with open('C:\\temp\\detection.xml', 'wb') as file:
        file.write(data)
    import xml.etree.ElementTree as ET
    root = ET.fromstring(data.decode('utf-8'))
    sub_item = root.findall('.//SerializedPpmDwnld')
    if sub_item is not None and len(sub_item) == 1 and sub_item[0].text:
        inner_xml_str = sub_item[0].text.strip()  # Get the inner XML string

        # Parse the inner XML
        inner_root = ET.fromstring(inner_xml_str)

        # Print the tag of the new root element
        print(inner_root.tag)

        # Iterate over inner elements (if needed)
        for child in inner_root:
            print(child.tag, child.text)
    print(sub_item)



    hex_data = bytes.fromhex('650002000490000001000000e0000000010000001d000000446573632052756e2054696d6500000032355f382d432d31420000000000000054696d652f4465707468000000000000000000000000000000000000000000000001020054696d652f4465707468000000000000000000000000000000000000000000000000000054696d65202620446174650000000000000000000000000000000000000000000000000003000000080000000300000054696d652026204461746500000000000800080003000300426c6f636b20506f736974696f6e00000800100003000300526973657220506f736974696f6e0000')
    hex_data = bytes.fromhex('65000200049000000100000014010000010000001c000000446573632052756e2054696d6500000032355f382d432d31420000000000000054696d652f4465707468000000000000000000000000000000000000000000000001220054696d652f4465707468000000000000000000000200000000000000000000000000f03f54696d652026204461746500000000000100000001000000ffffffff00000000000000000000000000000000000000000000000000000000000000000000000003000000ffffffff0000000000000000000000000000000003000000040000000200010054696d652026204461746500000000000800080003000300446570746800000000000000000000000400100003000300426c6f636b20506f736974696f6e0000')
    AdiCommands.AdiCommands.DataSetPrepareComplex.CreateCommandFromBinaryData(adi_client, AdiDefinitions.MessageHeader(data=hex_data), hex_data)

    local_host, local_port = adi_client.writer.get_extra_info("sockname")
    print(f"Client '{local_host}' connected from port {local_port}")

    ds = await adi_client.OpenDataSet(record="iTom Save", description="CurrentData", bag_mode=True)
    files = await ds.GetFilesList()
    data = await ds.ReadFile(files[0]['EntryName'])
    await ds.Close()
    obj = json.loads(data.decode('utf8'))
    print(sys.getsizeof(obj))

    ds = await adi_client.OpenDataSetComplex(output_resolution=0.1524,
        iv={"Variable": AdiDefinitions.AdiVariable(name="Depth")},
        keys=[
            AdiDefinitions.AdiDataSet(well=None, run_alias="Well Based", record="Desc Run Depth", description="MWD-T", descriptor_record="ALD Azi HS RT", variables=[
                AdiDefinitions.AdiVariableComplex(name="HDBQ", coercion_type=AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.Smooth, coercion_param=0.183, gap_distance=0.1524)),
                AdiDefinitions.AdiVariableComplex(name="HRBQ", coercion_type=AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.Smooth, coercion_param=0.183, gap_distance=0.1524))
            ]),
            AdiDefinitions.AdiDataSet(well=None, run_alias="Well Based", record="Desc Run Depth", description="MWD-T", descriptor_record="CTN Porosity RT", variables=[
                AdiDefinitions.AdiVariableComplex(name="LS Porosity", coercion_type=AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.Smooth, coercion_param=0.183, gap_distance=0.1524))
            ]),
            AdiDefinitions.AdiDataSet(well=None, run_alias="Well Based", record="Desc Run Depth", description="MWD-T", descriptor_record="DGR", variables=[
                AdiDefinitions.AdiVariableComplex(name="Gamma Ray", coercion_type=AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.Smooth, coercion_param=0.183, gap_distance=0.1524))
            ]),
            AdiDefinitions.AdiDataSet(well=None, run_alias="Well Based", record="Desc Run Depth", description="MWD-T", descriptor_record="EWR 09T", variables=[
                AdiDefinitions.AdiVariableComplex(name="EWR Phase Res", coercion_type=AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.Smooth, coercion_param=0.183, gap_distance=0.1524))
            ]),
            AdiDefinitions.AdiDataSet(well=None, run_alias="Well Based", record="Desc Run Depth", description="MWD-T", descriptor_record="EWR 15T", variables=[
                AdiDefinitions.AdiVariableComplex(name="EWR Phase Res", coercion_type=AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.Smooth, coercion_param=0.183, gap_distance=0.1524))
            ]),
            AdiDefinitions.AdiDataSet(well=None, run_alias="Well Based", record="Desc Run Depth", description="MWD-T", descriptor_record="EWR 27T", variables=[
                AdiDefinitions.AdiVariableComplex(name="EWR Phase Res", coercion_type=AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.Smooth, coercion_param=0.183, gap_distance=0.1524))
            ]),
            AdiDefinitions.AdiDataSet(well=None, run_alias="Well Based", record="Desc Run Depth", description="MWD-T", descriptor_record="EWR 39T", variables=[
                AdiDefinitions.AdiVariableComplex(name="EWR Phase Res", coercion_type=AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.Smooth, coercion_param=0.183, gap_distance=0.1524))
            ]),
            AdiDefinitions.AdiDataSet(well=None, run_alias="Well Based", record="Desc Run Depth", description="MWD-T", descriptor_record="RG GR RT", variables=[
                AdiDefinitions.AdiVariableComplex(name="Gamma Ray", coercion_type=AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.Smooth, coercion_param=0.183, gap_distance=0.1524))
            ]),
            AdiDefinitions.AdiDataSet(well=None, run_alias="Well Based", record="Desc Run Depth", description="MWD-T", descriptor_record="PWD Avg Press", variables=[
                AdiDefinitions.AdiVariableComplex(name="Poff AnP - EMW", coercion_type=AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.LastInInterval, gap_distance=0.1524))
            ]),
            AdiDefinitions.AdiDataSet(well=None, run_alias="Well Based", record="Desc Run Depth", description="Logging", descriptor_record="ROP", variables=[
                AdiDefinitions.AdiVariableComplex(name="ROP Inst", coercion_type=AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.Smooth, coercion_param=0.4, gap_distance=0.1524))
            ])
        ], include_iv=True)
    await adi_client.SendNewCommand(AdiCommands.AdiCommands.DataSetSetSmoothUnknown(adi_client, ds, 1300, 0, 0))
    # data = await ds.ReadNext(1)
    # response = await adi_client.SendNewCommand(AdiCommands.AdiCommands.DataSetRead(adi_client, adi_dataset=ds, read_previous=False))

    # await adi_client.SendNewCommand(AdiCommands.AdiCommands.DataSetSetSmoothUnknown2(adi_client, ds, 2000, 0, 0x4d7f51bc))
    import datetime
    lines = []
    max_chars = [7] * 12
    while True:
        data = await ds.ReadNext(0x32)
        if data == None or len(data) == 0: break
        lines += data
        for d in data:
            for i in range(len(d)):
                if d[i] != None and abs(d[i]) > max_chars[i]: max_chars[i] = abs(d[i])
    await ds.Close()
    print(f"{sys.getsizeof(lines)} bytes")

    k1 = AdiDefinitions.AdiDataSetPrimaryKey(well="35_6-5S", run_number=0, record="Desc Run Time", description="Time/Depth", descriptor_record="Time/Depth")
    k2 = AdiDefinitions.AdiDataSetPrimaryKey(well="35_6-5S", run_number=0, record="Desc Run Time", description="SDL", descriptor_record="Time SDL Fast")
    keys = [k1, k2]
    filter_activities_per_key = None
    iv = {"Variable": AdiDefinitions.AdiVariable(name="Time & Date", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=0))), "UnitOption": AdiDefinitions.UnitOption(id=0)}
    coercions = []
    vars = [
        {"Variable": AdiDefinitions.AdiVariable(size=8, offset=0, format=AdiEnums.StorageType.NUMBER_DECIMAL, name="Time & Date", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=0))), "UnitOption": AdiDefinitions.UnitOption(id=0)},
        {"Variable": AdiDefinitions.AdiVariable(size=8, offset=16, format=AdiEnums.StorageType.NUMBER_DECIMAL, name="Depth", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=3))), "UnitOption": AdiDefinitions.UnitOption(id=3)},
        {"Variable": AdiDefinitions.AdiVariable(size=8, offset=24, format=AdiEnums.StorageType.NUMBER_DECIMAL, name="Hole Depth", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=3))), "UnitOption": AdiDefinitions.UnitOption(id=3)},
        {"Variable": AdiDefinitions.AdiVariable(size=8, offset=8, format=AdiEnums.StorageType.NUMBER_DECIMAL, name="WOB Avg", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=7))), "UnitOption": AdiDefinitions.UnitOption(id=7)},
        {"Variable": AdiDefinitions.AdiVariable(size=8, offset=24, format=AdiEnums.StorageType.NUMBER_DECIMAL, name="Hookload Avg", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=3))), "UnitOption": AdiDefinitions.UnitOption(id=3)},
        {"Variable": AdiDefinitions.AdiVariable(size=8, offset=24, format=AdiEnums.StorageType.NUMBER_DECIMAL, name="RPM Surface Avg", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=3))), "UnitOption": AdiDefinitions.UnitOption(id=3)},
        {"Variable": AdiDefinitions.AdiVariable(size=8, offset=32, format=AdiEnums.StorageType.NUMBER_DECIMAL, name="Torque Abs Avg", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=3))), "UnitOption": AdiDefinitions.UnitOption(id=3)},
        {"Variable": AdiDefinitions.AdiVariable(size=8, offset=40, format=AdiEnums.StorageType.NUMBER_DECIMAL, name="SPP1 Avg", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=0x1a))), "UnitOption": AdiDefinitions.UnitOption(id=0x1a)},
        {"Variable": AdiDefinitions.AdiVariable(size=8, offset=48, format=AdiEnums.StorageType.NUMBER_DECIMAL, name="Flow In Pum Avg", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=0x0c))), "UnitOption": AdiDefinitions.UnitOption(id=0x0c)},
        {"Variable": AdiDefinitions.AdiVariable(size=8, offset=56, format=AdiEnums.StorageType.NUMBER, name="CAM Stroke cts", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=0))), "UnitOption": AdiDefinitions.UnitOption(id=0)},
        {"Variable": AdiDefinitions.AdiVariable(size=8, offset=64, format=AdiEnums.StorageType.NUMBER_DECIMAL, name="Flow Out Avg", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=0x0c))), "UnitOption": AdiDefinitions.UnitOption(id=0x0c)},
        {"Variable": AdiDefinitions.AdiVariable(size=8, offset=72, format=AdiEnums.StorageType.NUMBER_DECIMAL, name="Gas Hydrcbn Avg", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=3))), "UnitOption": AdiDefinitions.UnitOption(id=3)}
    ]
    vars_index_keys = [0xffffffff, 0, 0]
    output_resolution = 0
    ds = AdiCommands.AdiCommands.DataSetPrepareComplex(adi_client, keys=keys, filter_activities_per_key=filter_activities_per_key, variables=vars, coercion_types=coercions, iv=iv, output_resolution=output_resolution)
    bytes_data = ds.BuildCommandBinaryData()
    str_hex = bytes_data.hex()

    k1 = AdiDefinitions.AdiDataSetPrimaryKey(well="35_6-5S", run_number=400, record="DGR", description="Realtime")
    iv = AdiDefinitions.AdiVariable(name="Depth", unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=3)))
    iv = {"Variable": iv, "UnitOption": iv.unit_type.unit_option}
    coercion1 = AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.IndependentVariable)
    coercion2 = AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.Smooth, coercion_param=0.183)
    var1 = AdiDefinitions.AdiVariable(name="Depth", size=8, offset=0, format=AdiEnums.StorageType.NUMBER_DECIMAL, unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=3)))
    var2 = AdiDefinitions.AdiVariable(name="Gamma Ray", size=8, offset=8, format=AdiEnums.StorageType.NUMBER_DECIMAL, unit_type=AdiDefinitions.UnitType(unit_option=AdiDefinitions.UnitOption(id=1)))
    response = await adi_client.SendNewCommand(AdiCommands.AdiCommands.DataSetPrepareComplex(adi_client, keys=[k1], filter_activities_per_key=[1], variables=[{"Variable": var1, "UnitOption": var1.unit_type.unit_option}, {"Variable": var2, "UnitOption": var2.unit_type.unit_option}], coercion_types=[coercion1, coercion2], iv=iv, output_resolution=0.1524))
    ds = None if not response["Success"] else response["AdiDataSet"]
    # response = await adi_client.SendNewCommand(AdiCommands.AdiCommands.DataSetSetSmoothUnknown(adi_client, ds, 3335.49121554745272, 0x0a, 0x0759fed4))

    # response = await adi_client.SendNewCommand(AdiCommands.AdiCommands.DataSetPrepareComplex(adi_client, keys=[k1], filter_activities_per_key=[0], variables=[{"Variable": var1, "UnitOption": var1.unit_type.unit_option}], coercion_types=[], iv=iv, unknowns1=[0xffffffff]))
    # ds2 = None if not response["Success"] else response["AdiDataSet"]
    # response = await adi_client.SendNewCommand(AdiCommands.AdiCommands.DataSetSetSmoothUnknown2(adi_client, ds2, 3335.42639998664976, 0x00, 0x4d7f51bc))
    # response = await adi_client.SendNewCommand(AdiCommands.AdiCommands.DataSetRead(adi_client, ds2, read_previous=True))
    # data = None if not response["Success"] else response["Data"]
    # response = await adi_client.SendNewCommand(AdiCommands.AdiCommands.DataSetClose(adi_client, ds2))

    response = await adi_client.SendNewCommand(AdiCommands.AdiCommands.DataSetSetSmoothUnknown2(adi_client, ds, 3335.27399998664976, 0x00, 12000))# 0x4d7f51bc))
    response = await adi_client.SendNewCommand(AdiCommands.AdiCommands.DataSetReadWithLimit(adi_client, ds, 1000, 3433.07293554745272, AdiEnums.BlockReadOption.OnePointPast))
    data = None if not response["Success"] else response["Data"]
    if data == None: print("Deu ruim!")
    else: print(f"Number of records: {len(data)}")
    print("Finished!")

async def example2():
    adi_client:AdiClientToRemote.AdiClientToRemote = AdiClientToRemote.AdiClientToRemote(asyncio.get_event_loop(), host="11.11.0.102", enabled=True, realtime=False)
    while adi_client.connection_state != AdiDefinitions.ConnectionState.CONNECTED: await asyncio.sleep(0.1)

    keys:list[AdiDefinitions.AdiDataSet] = []
    datasets_added:list[AdiDefinitions.AdiDataSet] = []
    
    curves_rt:list[AdiDefinitions.LogCurve] = []
    curves_rt.append(AdiDefinitions.LogCurve(curve_type='WOB', record='Desc Run Time', description='SDL', desc_record='Time SDL Fast', variable='WOB Avg'))
    curves_rt.append(AdiDefinitions.LogCurve(curve_type='SPP', record='Desc Run Time', description='SDL', desc_record='Time SDL Fast', variable='SPP Avg'))
    curves_rt.append(AdiDefinitions.LogCurve(curve_type='Torque', record='Desc Run Time', description='SDL', desc_record='Time SDL Fast', variable='Torque Abs Avg'))
    curves_rt.append(AdiDefinitions.LogCurve(curve_type='Flow In', record='Desc Run Time', description='SDL', desc_record='Time SDL Fast', variable='Flow In Pum Avg'))
    curves_rt.append(AdiDefinitions.LogCurve(curve_type='RPM', record='Desc Run Time', description='SDL', desc_record='Time SDL Fast', variable='RPM Surface Avg'))
    curves_rt.append(AdiDefinitions.LogCurve(curve_type='Annular Press', record="Desc Rec Time", description='BTS', variable='Annular Press'))
    
    for key in curves_rt:
        if any(k.description == key.description and k.descriptor_record == key.desc_record for k in datasets_added): continue
        datasets_added.append(AdiDefinitions.AdiDataSet(description=key.description, descriptor_record=key.desc_record))
        variables = []
        for k in curves_rt:
            if k.description == key.description and k.desc_record == key.desc_record:
                variables.append(AdiDefinitions.AdiVariableComplex(name=k.variable, coercion_type = AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.Smooth, coercion_param=8, gap_distance=5)))
        # keys.append(AdiDefinitions.AdiDataSet(run_alias="Well Based", record='Desc Run Time', description=key.description, descriptor_record=key.desc_record, variables=variables))
        keys.append(AdiDefinitions.AdiDataSet(run_alias="Well Based", record=key.record, description=key.description, descriptor_record=key.desc_record, variables=variables))
    keys[-1].variables[-1].coercion_type = AdiDefinitions.CoercionType(coercion_type=AdiEnums.CoercionTypes.Last, gap_distance=10)

    start_time = datetime.datetime.strptime("2025-05-21T06:15:00.000000+02:00", "%Y-%m-%dT%H:%M:%S.%f%z")
    lines = []
    try:
        ds = await adi_client.OpenDataSetComplex(output_resolution=1, iv={"Variable": AdiDefinitions.AdiVariable(name="Time & Date")}, keys=keys, include_iv=True)
        if ds != None:
            for i in range(len(curves_rt)):
                curves_rt[i].unit_option = ds.variables[i]["UnitOption"]
            await ds.SetPositionTime(start_time)
            while True:
                data = await ds.ReadNext(0x320)
                if data == None or len(data) == 0: break
                lines += data
            await ds.Close()
    except Exception as ex:
        print(ex)
    return lines

asyncio.run(example2())
asyncio.sleep(1000)
exit()






# import math
# import zlib

# def copy_binary_section(source, destination, index_a, index_b):
#     # Ensure indices are valid
#     if index_a < 0 or index_b <= index_a:
#         raise ValueError("Invalid indices: ensure 0 <= index_a < index_b")

#     # Open the source file in binary read mode and the destination file in binary write mode
#     with open(source, 'rb') as src_file:
#         src_file.seek(index_a)  # Move to the starting index
#         data = src_file.read(index_b - index_a)  # Read the specified section

#     # Write the extracted data to the destination file
#     with open(destination, 'wb') as dest_file:
#         dest_file.write(data)

# def beautify_hex(arr, show_per_line=16, show_per_separator=8):
#     str_line = "00000    "
#     str_chars = ""
#     for i in range(len(arr)):
#         n = arr[i]
#         str_number = chr(n).rjust(1) if 0x20 <= n <= 0x7e else '\u00b7'
#         if n == 0: str_line += f"\033[1;30;40m{hex(n)[2:].rjust(2, '0')}\033[0m "
#         elif (n == 0x78 and 0 <= i <= len(arr) - 4 and list(arr[i + 0:i + 4]) == [0x78, 0x56, 0x34, 0x12]) or \
#             (n == 0x56 and 1 <= i <= len(arr) - 3 and list(arr[i - 1:i + 3]) == [0x78, 0x56, 0x34, 0x12]) or \
#             (n == 0x34 and 2 <= i <= len(arr) - 2 and list(arr[i - 2:i + 2]) == [0x78, 0x56, 0x34, 0x12]) or \
#             (n == 0x12 and 3 <= i <= len(arr) - 1 and list(arr[i - 3:i + 1]) == [0x78, 0x56, 0x34, 0x12]):
#             str_line += f"\033[1;35;40m{hex(n)[2:].rjust(2, '0')}\033[0m "
#         else: str_line += f"{hex(n)[2:].rjust(2, '0')} "
#         str_chars += f"{str_number}"
#         if i % show_per_separator == 7 and i % show_per_line != 15:
#             str_line += "  "
#             str_chars += " "
#         if i % show_per_line == 15 or i == len(arr) - 1:
#             spaces_extra = (show_per_line - (i % show_per_line) - 1) * 3 + (0 if i % show_per_line > show_per_separator else 2)
#             print(str_line + (" " * spaces_extra) + "    " + str_chars)
#             str_line = f"{hex(int(math.floor((i + 1) / show_per_line)))[2:].rjust(4, '0')}0    "
#             str_chars = ""

# def show_binary_file(file_path):
#     # Read file content as bytes
#     with open(file_path, 'rb') as file:
#         bytes_read = file.read()
#     beautify_hex(bytes_read)

# copy_binary_section("C:/temp/teste.adi", "C:/temp/teste.xml", 0x240, 0x138e)
# copy_binary_section("C:/temp/teste.adi", "C:/temp/zlib.dat", 19290 - 10, 19290 + 600)
# show_binary_file("C:/temp/teste.adi")

# # The hexadecimal data as bytes
# with open("C:/temp/teste.adi", 'rb') as src_file:
#     src_file.seek(19290)  # Move to the starting index
#     data = src_file.read(20835 - 19290)  # Read the specified section

# # Try decompressing from different offsets with raw Deflate
# for i in range(len(data)):
#     try:
#         decompressed_data = zlib.decompress(data[i:], wbits=-zlib.MAX_WBITS)  # Raw Deflate (-15 for maximum window size)
#         # print(f"Decompressed data at offset {i}:\n{decompressed_data.decode('utf-8', errors='ignore')}")
#         show_binary_hex(decompressed_data)
#         break
#     except zlib.error as e:
#         # Ignore decompression errors and continue with the next offset
#         pass
# print("Finished!")
