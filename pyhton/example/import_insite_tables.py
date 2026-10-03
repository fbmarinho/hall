import time
import mysql.connector
from adi.AdiClientToRemote import AdiClientToRemote, ConnectionState
from databasetablebuilder import CreateTables, PopulateFirstTables

my_host = "localhost"
my_user = "insite"
my_pass = "Nor1ns1te"
my_db_name = "insite1"
drop_db_if_exists = True

remote_insite = "192.168.25.81"

def ConnectToMySQLDB(db=None):
    try: return mysql.connector.connect(host=my_host, user=my_user, password=my_pass, raise_on_warnings=False, database=db)
    except:
        print(f"{'{:.3f}'.format(time.time() - start_time).rjust(8)} Could not connect to MySQL using the provided credentials.")
        exit(1)

start_time = time.time()

# Connecting to MySQL and opening main cursor
db = ConnectToMySQLDB()
time.sleep(0.5)
mycursor = db.cursor()

# First creating database
if drop_db_if_exists: mycursor.execute(f"DROP DATABASE IF EXISTS `{my_db_name}`")
else:
    mycursor.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME=%s", [my_db_name])
    if len(mycursor.fetchall()) > 0: raise Exception("Database already exists!")
mycursor = db.cursor()
mycursor.execute(f"CREATE DATABASE {my_db_name}")
mycursor.execute(f"USE {my_db_name}")

# Creating tables
cursor = db.cursor()
CreateTables(cursor, my_db_name)
cursor.close()
db.close()
time.sleep(1)

# Populating first tables
db = ConnectToMySQLDB(my_db_name)
mycursor = db.cursor()
PopulateFirstTables(mycursor, my_db_name, True)
db.commit()
print(f"{'{:.3f}'.format(time.time() - start_time).rjust(8)} Database and tables created...")


#---------------------------
# Connecting to remote server and getting tables structure
adi_client = AdiClientToRemote(remote_insite, False)
while adi_client.connection_state != ConnectionState.CONNECTED: time.sleep(0.1)
data_tables = adi_client.ReadAllDataTablesDefinitions()
print(f"{'{:.3f}'.format(time.time() - start_time).rjust(8)} Remote structure loaded...")

sql = f"INSERT INTO `{my_db_name}`.`measurement_classes` (name) VALUES (%s)"
sql_sub = f"INSERT INTO `{my_db_name}`.`mc_units` (measurement_classes_id, name_long, name_short, function_type, arg1, arg2, psl_types) VALUES (%s, %s, %s, %s, %s, %s, %s)"
sql_upd = f"UPDATE `{my_db_name}`.`measurement_classes` SET mc_default_id=%s WHERE id=%s"
for item in data_tables["Classes"]:
    val = (item.name,)
    mycursor.execute(sql, val)
    item.id = mycursor.lastrowid
    first_item = True
    for sub_item in item.unit_options:
        val = (item.id, sub_item["UnitOption"].long_name, sub_item["UnitOption"].short_name,
                sub_item["ConversionInfo"].function_type, sub_item["ConversionInfo"].arg1, sub_item["ConversionInfo"].arg2, sub_item["UnitOption"].psl_types)
        mycursor.execute(sql_sub, val)
        if first_item:
            val = (mycursor.lastrowid, item.id)
            mycursor.execute(sql_upd, val)
            first_item = False
db.commit()
print(f"{'{:.3f}'.format(time.time() - start_time).rjust(8)} Classes inserted...")

# unit_types.sort(key=lambda x: x.name)
sql = f"INSERT INTO `{my_db_name}`.`unit_types` (measurement_classes_id, name) VALUES (%s, %s)"
for item in data_tables["UnitTypes"]:
    val = (item.measurement_class.id, item.name)
    mycursor.execute(sql, val)
    item.id = mycursor.lastrowid
db.commit()
print(f"{'{:.3f}'.format(time.time() - start_time).rjust(8)} Unit Types inserted...")

# Options lists
sql = f"INSERT INTO `{my_db_name}`.`options_lists` (name, read_only) VALUES (%s, %s)"
sql_sub = f"INSERT INTO `{my_db_name}`.`options_lists_options` (name, options_lists_id) VALUES (%s, %s)"
for item in data_tables["OptionsLists"]:
    val = (item.name, item.read_only)
    mycursor.execute(sql, val)
    item.id = mycursor.lastrowid
    for sub_item in item.options:
        val = (sub_item, item.id)
        mycursor.execute(sql_sub, val)
db.commit()
print(f"{'{:.3f}'.format(time.time() - start_time).rjust(8)} Options Lists inserted...")

# variables.sort(key=lambda x: x.name)
sql = f"INSERT INTO `{my_db_name}`.`variables` (name, mnemonic, curve_label, unit_types_id, variables_types_id, special, size, number_of_elements, number_of_decimals, mnemonic32, options_lists_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
for item in data_tables["Variables"]:
    val = (item.name, item.mnemonic, item.curve_label, item.unit_type.id, item.var_type.value, item.special,
            item.size, item.number_of_elements, item.number_of_decimals, item.mnemonic32, None if item.options_list == None else item.options_list.id)
    mycursor.execute(sql, val)
    item.id = mycursor.lastrowid
db.commit()
print(f"{'{:.3f}'.format(time.time() - start_time).rjust(8)} Variables inserted...")

# Records
sql = f"INSERT INTO `{my_db_name}`.`records` (name, records_types_id, index_types, records_categories_id, primary_keys, psl_types, attributes) VALUES (%s, %s, %s, %s, %s, %s, %s)"
sql_sub = f"INSERT INTO `{my_db_name}`.`records_variables` (records_id, variables_id, calculated, mnemonic, curve_label, mnemonic32, algorithms_calculation_id, reference_variable_id, coeff1, coeff2, coeff3) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
for item in data_tables["Records"]:
    val = (item.name, item.record_type_id, item.index_types,
            item.category_id, item.primary_keys, item.psl_types, item.attributes)
    mycursor.execute(sql, val)
    item.id = mycursor.lastrowid
    for sub_item in item.variables:
        var_ref_id = None if sub_item.ref_variable == None else sub_item.ref_variable.id
        val = (item.id, sub_item.variable.id, sub_item.calculated, sub_item.mnemonic, sub_item.curve_label, sub_item.mnemonic32,
                sub_item.algorithm, var_ref_id,
                0 if sub_item.coeff1 == None else sub_item.coeff1,
                0 if sub_item.coeff2 == None else sub_item.coeff2,
                0 if sub_item.coeff3 == None else sub_item.coeff3)
        mycursor.execute(sql_sub, val)
db.commit()
print(f"{'{:.3f}'.format(time.time() - start_time).rjust(8)} Records inserted...")
print("Finished!")
