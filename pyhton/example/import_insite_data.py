import copy
import threading
import time
import mysql.connector
from adi.AdiClientToRemote import AdiClientToRemote, ConnectionState
from adi.AdiCommands import AdiCommands
from adi.AdiEnums import RecordOpenModes
from databasetablebuilder import CreateTables, PopulateFirstTables

my_host = "localhost"
my_user = "insite"
my_pass = "Nor1ns1te"
my_db_name = "insite1"
drop_db_if_exists = True

remote_insite = "192.168.25.81"
remote_insite = "10.206.176.71"
remote_insite = "10.10.0.50"

def ConnectToMySQLDB(db=None):
    try: return mysql.connector.connect(host=my_host, user=my_user, password=my_pass, raise_on_warnings=False, database=db)
    except:
        print(f"{'{:.3f}'.format(time.time() - start_time).rjust(8)} Could not connect to MySQL using the provided credentials.")
        exit(1)

start_time = time.time()

# Connecting to MySQL and opening main cursor
db = ConnectToMySQLDB(my_db_name)
time.sleep(0.5)
mycursor = db.cursor()

# Cleaning everything at first
mycursor = db.cursor()
mycursor.execute(f"SHOW TABLES")
tables = mycursor.fetchall()
for (t,) in tables:
    if t.startswith("z_"): mycursor.execute(f"DROP TABLE `{t}`")
mycursor.execute("SET FOREIGN_KEY_CHECKS = 0")
mycursor.execute(f"TRUNCATE TABLE `variables_vector_attributes`")
mycursor.execute(f"TRUNCATE TABLE `data_tables`")
mycursor.execute(f"TRUNCATE TABLE `current_job`")
mycursor.execute(f"TRUNCATE TABLE `runs`")
mycursor.execute(f"TRUNCATE TABLE `wells`")
mycursor.execute("SET FOREIGN_KEY_CHECKS = 1")
print(f"{'{:.3f}'.format(time.time() - start_time).rjust(8)} Cleared tables...")

#---------------------------
# Connecting to remote server and getting tables structure
adi_client = AdiClientToRemote(remote_insite, False)
while adi_client.connection_state != ConnectionState.CONNECTED: time.sleep(0.1)
datasets = adi_client.QueryRecDesc()

next_run_number = 11123
wells = []
for ds in datasets:
    well = next((x for x in wells if x["name"] == ds.well), None)
    if well == None:
        mycursor.execute("INSERT INTO wells (name) VALUES (%s)", (ds.well,))
        well = {"id": mycursor.lastrowid, "name": ds.well, "runs": []}
        wells.append(well)
    run = next((x for x in well["runs"] if x["run_alias"] == ds.run), None)
    if run == None:
        run_number = 0
        run_alias = None
        if str(ds.run).isnumeric():
            run_number = int(ds.run)
            run_alias = f"{ds.run:0>4}"
        else:
            run_alias = ds.run
            run_number = 0 if ds.run == "Well Based" else next_run_number
            next_run_number += 1

        mycursor.execute("INSERT INTO runs (wells_id, run_alias, run_number) VALUES (%s, %s, %s)", (well["id"], run_alias, run_number))
        run = {"id": mycursor.lastrowid, "run_alias": run_alias, "run_number": run_number, "records": []}
        well["runs"].append(run)
    record = next((x for x in run["records"] if x["record"].name == ds.record), None)
    if record == None:
        cmd = AdiCommands.QueryRecordAttributesEx(record_name=ds.record)
        result = cmd.GetLocalResult(db)
        if not "Record" in result:
            #raise Exception(f"Record \"{ds.record}\" not found")
            print(f"Record \"{ds.record}\" not found")
            continue
        record_data = result["Record"]
        record = {"record": record_data, "descriptions": []}
        run["records"].append(record)
    record["descriptions"].append(ds.description)
    # mycursor.execute("INSERT INTO data_tables (wells_id, runs_id, records_id, description) VALUES (%s, %s, %s, %s)", (well["id"], run["id"], record["record"].id, ds.description))
db.commit()
print(f"{'{:.3f}'.format(time.time() - start_time).rjust(8)} Wells and runs created...")

# Retrieving all unit options
finished_ev = threading.Event()
def __queryOptionsResponse(cmd, response):
    result = cmd.TranslateResponseFromBytes(response)
    for i in range(len(adi_client.unit_types)):
        ut = adi_client.unit_types[i]
        ut.unit_options = copy.copy(result["UnitTypes"][i].unit_options)
        uo = ut.unit_option
        if uo != None:
            for j in range(len(ut.unit_options)):
                if ut.unit_options[j].short_name == uo.short_name:
                    uo.id = j
                    break
    finished_ev.set()
adi_client.SendNewCommand(AdiCommands.QueryUnitTypesOptions(adi_client, __queryOptionsResponse, range(len(adi_client.unit_types))))
finished_ev.wait(100)

for w in wells:
    for r in w["runs"]:
        for rec in r["records"]:
            for description in rec["descriptions"]:
                well, run_number, record = w["name"], r["run_number"], rec["record"].name
                ds_bag = adi_client.OpenDataSet(well, run_number, record, description, bag_mode=True)
                
                bagdata_values = []
                if len(ds_bag.variables) > 0: bagdata_values = ds_bag.ReadBagData()
                ds_bag.Close()
                
                # Opening the dataset
                cmd = AdiCommands.DataSetPrepare(well=well, run_number=run_number, record=record, description=description, open_mode_value=RecordOpenModes.Create)
                result = cmd.GetLocalResult(db)
                if not result["Success"]: raise Exception("Issue here!")
                elif not "DSReader" in result: raise Exception("Issue here!")
                
                if len(ds_bag.variables) > 0:
                    cmd_write = AdiCommands.DataSetWriteBagData(adi_dataset=result["DSReader"], variables=ds_bag.variables, values=bagdata_values)
                    result = cmd_write.GetLocalResult(db)
                    


# for ds in datasets:
#     ds_bag = adi_client.OpenDataSet(ds.well, ds.run_number, ds.record, ds.description, bag_mode=True)
#     bagdata = []
#     if len(ds_bag.variables) > 0:
#         data = ds_bag.ReadBagData()
#         for i in range(len(ds_bag.variables)):
#             bagdata.append({"Variable": ds_bag.variables[i], "Data": data[i]})
#     ds_bag.Close()
    
#     ds_data = adi_client.OpenDataSet(well=ds.well, run_number=ds.run_number, record=ds.record, description=ds.description)
#     if ds_data == None: continue
    
#     total_lines = ds_data.GetNumberOfRecords()
    
#     data_content = []
#     lines_per_read = 1
#     last_total_bytes_recv = adi_client.total_bytes_received
#     lines_remaining = total_lines
#     while lines_remaining > 0:
#         lines_to_read = lines_per_read if lines_remaining > lines_per_read else lines_remaining
#         line_to_read = 1
#         data = ds_data.ReadNext(lines_to_read)

#         if lines_remaining == total_lines:
#             # first read
#             est_size = adi_client.total_bytes_received - last_total_bytes_recv
#             max_bytes = 5 * 1024 * 1024
#             lines_per_read = int(max_bytes / est_size)
#             if lines_per_read > lines_remaining: lines_per_read = total_lines
#             if lines_per_read == 0: lines_per_read = 1
#             str_time = format((time.time_ns() - start_time) / 10e8, ".3f").rjust(10) + " - "
#             print(f"{str_time}Reading {ds.well}\\{ds.run_number}\\{ds.record}\\{ds.description} - every {lines_per_read} from {total_lines} (est. size={est_size})")

#         lines_remaining -= lines_to_read
#         data_content += data
#     ds_data.Close()
#     datasets_with_data.append({ "DataSet": ds, "BagData": bagdata, "Variables": ds_data.variables, "Data": data_content })
    
# print("Finished reading everything!")


print(f"{'{:.3f}'.format(time.time() - start_time).rjust(8)} Finished!")
print("Tada!")