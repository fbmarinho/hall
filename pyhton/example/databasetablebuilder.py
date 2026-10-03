import mysql.connector
import sys
import re
import time

(host, user, pwd, db) = (None, None, None, None)


class MeasurementClassUnit():
    def __init__(self, name_long=None, name_short=None, function_type=0, arg1=0.0, arg2=0.0, default=False, psl_types=0):
        self.name_long = name_long
        self.name_short = name_short
        self.function_type = function_type
        self.arg1 = arg1
        self.arg2 = arg2
        self.psl_types = psl_types
        self.default = default


class MeasurementClass():
    def __init__(self, name=None):
        self.id = 0
        self.name = name
        self.mc_units = []
        self.unit_types = []


class UnitType():
    def __init__(self, name=None, parent=None):
        self.id = 0
        self.name = name
        self.mc_parent = parent


class Variable():
    def __init__(self, name=None, mnemonic=None, curve_label=None, unit_type=None, var_type_str=None, special_str=None, number_of_decimals=0, mnemonic32=None):
        self.id = 0
        self.name = name
        self.mnemonic = None if len(mnemonic) == 0 else mnemonic
        self.curve_label = None if len(curve_label) == 0 else curve_label
        self.unit_type = unit_type
        self.number_of_elements = 1
        self.size = 1
        self.var_type = 0
        self.IdentifyVarType(var_type_str)
        self.special = 0
        self.IdentifySpecial(special_str)
        self.number_of_decimals = 0 if number_of_decimals < 0 else number_of_decimals
        self.mnemonic32 = None if len(mnemonic32) == 0 else mnemonic32
        self.option_lists = []
        self.is_option_list_read_only = None

    def IdentifyVarType(self, var_type_str):
        # ADI_VT_ARRAY = __MIN_INT,
        # ADI_VT_NONE = 0,
        # ADI_VT_CHAR = 1,
        # ADI_VT_UCHAR = 2,
        # ADI_VT_SHORT = 3,
        # ADI_VT_USHORT = 4,
        # ADI_VT_INT = 5,
        # ADI_VT_LONG = 5,
        # ADI_VT_UINT = 6,
        # ADI_VT_ULONG = 6,
        # ADI_VT_FLOAT = 7,
        # ADI_VT_DOUBLE = 8,
        # ADI_VT_STRING = 9,
        # ADI_VT_PCHAR = 10,
        # ADI_VT_BINARY = 11,
        # ADI_VT_PBYTE = 12,
        # ADI_VT_ENUM = 13

        upper = var_type_str.upper()

        if upper == "I1":
            self.size = 1
            self.var_type = 1
        elif upper == "I2":
            self.size = 2
            self.var_type = 3
        elif upper == "I4":
            self.size = 4
            self.var_type = 5
        elif upper == "U1":
            self.size = 1
            self.var_type = 2
        elif upper == "U2":
            self.size = 2
            self.var_type = 4
        elif upper == "U4":
            self.size = 4
            self.var_type = 6
        elif upper == "F4":
            self.size = 4
            self.var_type = 7
        elif upper == "F8":
            self.size = 8
            self.var_type = 8
        elif var_type_str.startswith("C"):
            self.size = int(var_type_str[1:])
            self.var_type = 9
        elif upper == "P4":
            self.size = 4
            self.var_type = 10
        elif upper == "Q4":
            self.size = 4
            self.var_type = 12
        else:
            pattern = re.compile(
                "([A-z0-9]+)[\\[\\(]([0-9]+)[\\]\\)]", re.IGNORECASE)
            result = pattern.search(var_type_str)
            if result != None:
                self.IdentifyVarType(result.group(1))
                self.number_of_elements = int(result.group(2))
            else:
                print("deu ruim!")

    def IdentifySpecial(self, special_str):
        # Nothing = 0,
        # Calculated = 1,
        # OptionList = 2,
        # DerivedDepth = 4,
        # DateFormat = 8,
        # WaveForm = 16,
        # EnumList = 32,
        # BoundArray = 64,
        # VectorData = 256

        lower = special_str.lower()
        self.special = 0
        if "c" in lower:
            self.special += 1
        if "o" in lower:
            self.special += 2
        if "e" in lower:
            self.special += 32
        if "t" in lower:
            self.special += 8
        if "d" in lower:
            self.special += 4
        if "w" in lower:
            self.special += 16
        if "l" in lower:
            self.special += 64
        if "v" in lower:
            self.special += 256


class RecordType():
    def __init__(self, name=None, id=0):
        self.name = name
        self.id = id


class RecordVariable():
    def __init__(self, variable=None, calculated=True, mnemonic=None, curve_label=None, mnemonic32=None, algorithm=None, var_ref=None, coeff1=0, coeff2=0, coeff3=0):
        self.variable = variable
        self.calculated = calculated
        self.mnemonic = None if len(mnemonic) == 0 else mnemonic
        self.curve_label = None if len(curve_label) == 0 else curve_label
        self.mnemonic32 = None if len(mnemonic32) == 0 else mnemonic32
        self.algorithm = algorithm
        self.var_ref = var_ref
        self.coeff1 = coeff1
        self.coeff2 = coeff2
        self.coeff3 = coeff3


class Record():
    def __init__(self, name=None, record_type_id=0, index_types=0, category=None, primary_keys=0, psl_types=0, attributes=0):
        self.name = name
        self.record_type_id = record_type_id
        self.index_types = index_types
        self.category = None if len(category) == 0 else category
        self.primary_keys = primary_keys
        self.psl_types = psl_types
        self.attributes = attributes
        self.variables = []


def PrintTime(total_seconds):
    number_hours = 0
    number_minutes = 0
    number_seconds = 0
    if total_seconds > 3600:
        temp = total_seconds % 3600
        number_hours = int((total_seconds - temp) / 3600)
        total_seconds = temp
    if total_seconds > 60:
        temp = total_seconds % 60
        number_minutes = int((total_seconds - temp) / 60)
        total_seconds = temp
    number_seconds = int(total_seconds)
    text = ""
    if number_hours > 0:
        text += f"{number_hours} hour{"s" if number_hours != 1 else ""}"
    if number_minutes > 0:
        text += f"{", " if len(text) > 0 else ""}{number_minutes} minute{
            "s" if number_minutes != 1 else ""}"
    text += f"{" and " if len(text) > 0 else ""}{number_seconds} second{
        "s" if number_seconds != 1 else ""}"
    print(text)


def GetCommandLineArgs():
    host = "localhost"
    user = "root"
    pwd = ""
    db = ""
    txt = ""
    next = ""
    for arg in sys.argv:
        txt = ""
        if arg == "-p":
            next = "pwd"
        elif arg == "-d":
            next = "db"
        elif arg == "-u":
            next = "user"
        elif arg == "-h":
            next = "host"
        elif next == "pwd":
            pwd = arg
            next = ""
        elif next == "db":
            db = arg
            next = ""
        elif next == "user":
            user = arg
            next = ""
        elif next == "host":
            host = arg
            next = ""
        else:
            txt = arg
            next = ""
    return (host, user, pwd, db, txt)


def ConnectToMySQLDB(db=None):
    try:
        if db == None:
            mydb = mysql.connector.connect(
                host=host,
                user=user,
                password=pwd,
                raise_on_warnings=True
            )
        else:
            mydb = mysql.connector.connect(
                host=host,
                user=user,
                password=pwd,
                raise_on_warnings=True,
                database=db
            )

        return mydb
    except:
        print("Could not connect to MySQL using the provided credentials.")
        exit(1)


def ReadInputFile(txt):
    try:
        start_time = time.time()

        measurement_classes = []
        measurement_classes_names = []

        variables = []
        variables_names = []

        unit_types = []
        unit_types_names = []

        record_types = []
        record_types_names = []

        records = []

        algorithms = ["None", "Bit Test", "Reciprocal", "Vector Access", "Mod", "Digit", "Linear Equation"]

        file = open(txt, 'r')
        curr_session = ""
        last_obj = None

        number_of_lines = 0
        print("Counting number of lines...")
        while True:
            line = file.readline()
            number_of_lines += 1
            if not line:
                break

        file.seek(0)
        print("Loading objects to memory...")

        counter = 0
        last_report = 0
        while True:
            line = file.readline()
            counter += 1
            percentage = int(counter / number_of_lines * 100)
            if percentage != last_report:
                print(f"{percentage}% processed")
                last_report = percentage

            if not line:
                break

            if line.startswith("#"):
                continue
            if line.startswith(":"):
                curr_session = line[1:].strip().lower()
                last_obj = None
            else:
                match(curr_session):
                    case "measurement classes":
                        if line.isspace() or len(line) == 0:
                            last_obj = None
                            continue
                        if not line.startswith(" "):
                            data = line.split(";")
                            if len(data) >= 3:
                                last_obj = MeasurementClass(
                                    name=data[0].strip())
                                measurement_classes.append(last_obj)
                                measurement_classes_names.append(
                                    last_obj.name.lower())

                                mc_unit = MeasurementClassUnit(name_long=data[1].strip(), name_short=data[2].strip(), default=True)
                                last_obj.mc_units.append(mc_unit)
                        elif last_obj != None:  # and line.startswith(" ")
                            data = line.split(";")
                            if len(data) >= 5:
                                mc_unit = MeasurementClassUnit(name_long=data[0].strip(), name_short=data[1].strip(),
                                                               function_type=int(data[2].strip()), arg1=float(data[3].strip()),
                                                               arg2=float(data[4].strip()), flags=int(data[5].strip()))
                                last_obj.mc_units.append(mc_unit)

                    case "unit types":
                        if line.isspace() or len(line) == 0:
                            last_obj = None
                            continue
                        if not line.startswith(" "):
                            data = line.split(";")
                            if len(data) >= 2:
                                mc_name = data[0].strip()
                                try:
                                    ix = measurement_classes_names.index(
                                        mc_name.lower())
                                    last_obj = measurement_classes[ix]
                                except:
                                    print(f"In the \"Unit Types\" section, the measurement class \"{
                                          mc_name}\" is invalid (not declared before)")
                                    exit(1)
                                name = data[1].strip()
                                unit_type = UnitType(
                                    name=name, parent=last_obj)
                                last_obj.unit_types.append(unit_type)
                                unit_types.append(unit_type)
                                unit_types_names.append(unit_type.name.lower())
                        elif last_obj != None:  # and line.startswith(" ")
                            data = line.split(";")
                            if len(data) >= 1:
                                name = data[0].strip()
                                unit_type = UnitType(
                                    name=name, parent=last_obj)
                                last_obj.unit_types.append(unit_type)
                                unit_types.append(unit_type)
                                unit_types_names.append(unit_type.name.lower())

                    case "variables":
                        data = line.split(";")
                        if len(data) >= 8:
                            unit_type_name = data[3].strip().lower()
                            unit_type = None
                            try:
                                ix = unit_types_names.index(unit_type_name)
                                unit_type = unit_types[ix]
                            except:
                                print(f"For the variable \"{data[0].strip()}\", the unit type \"{
                                    unit_type_name}\" is invalid (not declared before)")
                                exit(1)
                            last_obj = Variable(
                                name=data[0].strip(), mnemonic=data[1].strip(), curve_label=data[2].strip(),
                                unit_type=unit_type, var_type_str=data[4].strip(), special_str=data[5].strip(),
                                number_of_decimals=int(data[6].strip()), mnemonic32=data[7].strip())
                            variables.append(last_obj)
                            variables_names.append(last_obj.name.lower())

                    case "option lists":
                        if line.isspace() or len(line) == 0:
                            last_obj = None
                            continue
                        if not line.startswith(" "):
                            data = line.split(";")
                            if len(data) >= 3:
                                name = data[0].strip().lower()
                                try:
                                    ix = variables_names.index(name)
                                    last_obj = variables[ix]
                                except:
                                    print(f"In the Option Lists section, the variable \"{
                                          name}\" is invalid (not declared before)")
                                    exit(1)
                                last_obj.is_option_list_read_only = data[1].strip(
                                ) == "1"
                                last_obj.option_lists.append(data[2].strip())
                        elif last_obj != None:  # and line.startswith(" ")
                            data = line.split(";")
                            if len(data) >= 1:
                                last_obj.option_lists.append(data[0].strip())

                    case "record types":
                        data = line.split(";")
                        if len(data) >= 2:
                            name = data[0].strip()
                            record_types.append(RecordType(
                                name=name, id=int(data[1].strip())))
                            record_types_names.append(name.lower())

                    case "records":
                        if line.isspace() or len(line) == 0:
                            last_obj = None
                            continue
                        if line.startswith("RecDef;"):
                            data = line.split(";")
                            if len(data) >= 12:
                                rt = data[2].strip().lower()
                                try:
                                    ix = record_types_names.index(rt)
                                    record_type = record_types[ix]
                                except:
                                    print(f"Record \"{data[1].strip()} with type \"{
                                          data[2].strip()}\" invalid (not declared before)")
                                    exit(1)

                                # Index types:
                                # Sequential = 1,
                                # Time = 2,
                                # Depth = 4,
                                # Activity = 8,
                                # Free = 32768
                                index_types = 0
                                if "S" in data[3]:
                                    index_types = 1
                                elif "-" in data[3]:
                                    index_types = 32768
                                else:
                                    if "T" in data[3]:
                                        index_types += 2
                                    if "D" in data[3]:
                                        index_types += 4
                                    if "A" in data[3]:
                                        index_types += 8

                                # PKs:
                                # RECORD_PK_WELL = 1;
                                # RECORD_PK_BITRUN = 2;
                                # RECORD_PK_DESCRIPTION = 4;
                                pks = 0
                                if data[5].strip() == "2":
                                    pks += 1
                                if data[6].strip() == "2":
                                    pks += 2
                                if data[7].strip() == "2":
                                    pks += 4

                                # PSLs:
                                # RECORD_PSL_Baroid = 1;
                                # RECORD_PSL_Cementing = 2;
                                # RECORD_PSL_Logging = 4;
                                # RECORD_PSL_Petrosite = 8;
                                # RECORD_PSL_PE = 16;
                                # RECORD_PSL_SDBS = 32;
                                # RECORD_PSL_Sperry = 64;
                                # RECORD_PSL_TTTCP = 128;
                                # RECORD_PSL_UBA = 256;
                                # RECORD_PSL_NMR = 512;
                                # RECORD_PSL_WITSML = 1024;

                                # Attributes:
                                # Hidden = 1;
                                # ReadOnly = 2;
                                # Locked = 4;
                                attributes = 0
                                if data[9].strip() == "1":
                                    attributes += 1
                                if data[10].strip() == "1":
                                    attributes += 2
                                if data[11].strip() == "1":
                                    attributes += 4

                                categories = ["None", "Surface Logging", "MWD"]

                                last_obj = Record(
                                    name=data[1].strip(), record_type_id=record_type.id, index_types=index_types,
                                    category_id=categories.index(data[4].strip()), primary_keys=pks, psl_types=int(data[8].strip()),
                                    attributes=attributes)
                                records.append(last_obj)
                        elif last_obj != None:  # and line.startswith(" ")
                            data = line.split(";")
                            if len(data) >= 10:
                                name = data[0].strip().lower()
                                variable = None
                                try:
                                    ix = variables_names.index(name)
                                    variable = variables[ix]
                                except:
                                    print(f"Record \"{last_obj.name} references invalid variable \"{
                                          name}\" (not declared before)")
                                    exit(1)

                                algorithm = data[5].strip()
                                if (len(algorithm) > 0):
                                    try:
                                        ix = algorithms.index(algorithm)
                                        algorithm = ix
                                    except:
                                        print(f"Record \"{last_obj.name} references invalid variable \"{
                                            name}\" (not declared before)")
                                        exit(1)

                                else:
                                    algorithm = None

                                var_ref = data[6].strip()
                                if len(var_ref) > 0:
                                    try:
                                        ix = variables_names.index(var_ref.lower())
                                        var_ref = variables[ix]
                                    except:
                                        var_ref = None
                                else: var_ref = None

                                record_var = RecordVariable(variable=variable, calculated=data[1].strip() == "0",
                                                            mnemonic=data[2].strip(), curve_label=data[3].strip(),
                                                            mnemonic32=data[4].strip(), algorithm=algorithm,
                                                            var_ref=var_ref,
                                                            coeff1=float(
                                                                data[7].strip()),
                                                            coeff2=float(
                                                                data[8].strip()),
                                                            coeff3=float(data[9].strip()))
                                last_obj.variables.append(record_var)

        file.close()

        total_seconds = time.time() - start_time
        PrintTime(total_seconds)

        return (measurement_classes, unit_types, variables, records, record_types)
    except Exception as e:
        print(f"It was not possible to read the specified file: {repr(e)}")
        exit(1)


def CheckIfDBExists():
    mydb = ConnectToMySQLDB()
    mycursor = mydb.cursor()
    mycursor.execute("SHOW DATABASES")
    for x in mycursor:
        if x == db:
            print("This DB name already exists")
            exit(1)
    mycursor.close()
    mydb.close()


def CreateTables(mycursor, db_name):
    sql = """
        SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
        SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
        SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

        -- -----------------------------------------------------
        -- Schema mydb
        -- -----------------------------------------------------

        -- -----------------------------------------------------
        -- Schema mydb
        -- -----------------------------------------------------
        CREATE SCHEMA IF NOT EXISTS `mydb` DEFAULT CHARACTER SET utf8 ;
        USE `mydb` ;

        -- -----------------------------------------------------
        -- Table `mydb`.`wells`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`wells` (
        `id` INT(5) NOT NULL AUTO_INCREMENT,
        `name` VARCHAR(45) NOT NULL,
        PRIMARY KEY (`id`))
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`runs`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`runs` (
        `id` INT(5) NOT NULL AUTO_INCREMENT,
        `wells_id` INT(5) NOT NULL,
        `run_alias` VARCHAR(45) NOT NULL,
        `run_number` INT(5) NOT NULL,
        PRIMARY KEY (`id`),
        INDEX `fk_runs_wells_idx` (`wells_id` ASC) VISIBLE,
        CONSTRAINT `fk_runs_wells`
            FOREIGN KEY (`wells_id`)
            REFERENCES `mydb`.`wells` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION)
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`records_types`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`records_types` (
        `id` INT(5) NOT NULL,
        `name` VARCHAR(45) NOT NULL,
        PRIMARY KEY (`id`))
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`records_categories`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`records_categories` (
        `id` INT(5) NOT NULL,
        `name` VARCHAR(45) NOT NULL,
        PRIMARY KEY (`id`))
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`records`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`records` (
        `id` INT(5) NOT NULL AUTO_INCREMENT,
        `name` VARCHAR(45) NOT NULL,
        `records_types_id` INT(5) NOT NULL,
        `index_types` INT(5) NOT NULL COMMENT 'RECORD_PK_WELL = 1;\nRECORD_PK_BITRUN = 2;\nRECORD_PK_DESCRIPTION = 4;',
        `records_categories_id` INT(5) NULL,
        `primary_keys` TINYINT(1) NOT NULL,
        `psl_types` INT NOT NULL,
        `attributes` INT NOT NULL,
        PRIMARY KEY (`id`),
        INDEX `fk_records_records_types1_idx` (`records_types_id` ASC) VISIBLE,
        INDEX `fk_records_records_categories1_idx` (`records_categories_id` ASC) VISIBLE,
        CONSTRAINT `fk_records_records_types1`
            FOREIGN KEY (`records_types_id`)
            REFERENCES `mydb`.`records_types` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION,
        CONSTRAINT `fk_records_records_categories1`
            FOREIGN KEY (`records_categories_id`)
            REFERENCES `mydb`.`records_categories` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION)
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`mc_units`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`mc_units` (
        `id` INT(5) NOT NULL AUTO_INCREMENT,
        `measurement_classes_id` INT(5) NOT NULL,
        `name_long` VARCHAR(45) NOT NULL,
        `name_short` VARCHAR(45) NOT NULL,
        `function_type` TINYINT(1) NOT NULL,
        `arg1` DOUBLE NOT NULL,
        `arg2` DOUBLE NOT NULL,
        `psl_types` INT NOT NULL,
        PRIMARY KEY (`id`),
        INDEX `fk_mc_units_measurement_classes1_idx` (`measurement_classes_id` ASC) VISIBLE,
        CONSTRAINT `fk_mc_units_measurement_classes1`
            FOREIGN KEY (`measurement_classes_id`)
            REFERENCES `mydb`.`measurement_classes` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION)
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`measurement_classes`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`measurement_classes` (
        `id` INT(5) NOT NULL AUTO_INCREMENT,
        `name` VARCHAR(45) NOT NULL,
        `mc_default_id` INT(5) NULL,
        PRIMARY KEY (`id`),
        INDEX `fk_measurement_classes_measurement_classes_units1_idx` (`mc_default_id` ASC) VISIBLE,
        CONSTRAINT `fk_measurement_classes_measurement_classes_units1`
            FOREIGN KEY (`mc_default_id`)
            REFERENCES `mydb`.`mc_units` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION)
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`unit_types`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`unit_types` (
        `id` INT(5) NOT NULL AUTO_INCREMENT,
        `measurement_classes_id` INT(5) NOT NULL,
        `name` VARCHAR(45) NOT NULL,
        PRIMARY KEY (`id`),
        INDEX `fk_unit_types_measurement_classes1_idx` (`measurement_classes_id` ASC) VISIBLE,
        CONSTRAINT `fk_unit_types_measurement_classes1`
            FOREIGN KEY (`measurement_classes_id`)
            REFERENCES `mydb`.`measurement_classes` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION)
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`variables_types`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`variables_types` (
        `id` INT(5) NOT NULL,
        `name` VARCHAR(45) NOT NULL,
        PRIMARY KEY (`id`))
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`options_lists`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`options_lists` (
        `id` INT NOT NULL AUTO_INCREMENT,
        `name` VARCHAR(45) NOT NULL,
        `read_only` TINYINT NOT NULL,
        PRIMARY KEY (`id`))
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`options_lists_options`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`options_lists_options` (
        `id` INT NOT NULL AUTO_INCREMENT,
        `options_lists_id` INT NOT NULL,
        `name` VARCHAR(100) NOT NULL,
        PRIMARY KEY (`id`),
        INDEX `fk_option_lists_options_options_lists1_idx` (`options_lists_id` ASC) VISIBLE,
        CONSTRAINT `fk_option_lists_options_options_lists1`
            FOREIGN KEY (`options_lists_id`)
            REFERENCES `mydb`.`options_lists` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION)
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`variables`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`variables` (
        `id` INT(5) NOT NULL AUTO_INCREMENT,
        `name` VARCHAR(45) NOT NULL,
        `mnemonic` VARCHAR(4) NULL,
        `curve_label` VARCHAR(45) NULL,
        `unit_types_id` INT(5) NOT NULL,
        `variables_types_id` INT(5) NOT NULL COMMENT 'ADI_VT_ARRAY = __MIN_INT,\nADI_VT_NONE = 0,\nADI_VT_CHAR = 1,\nADI_VT_UCHAR = 2,\nADI_VT_SHORT = 3,\nADI_VT_USHORT = 4,\nADI_VT_INT = 5,\nADI_VT_LONG = 5,\nADI_VT_UINT = 6,\nADI_VT_ULONG = 6,\nADI_VT_FLOAT = 7,\nADI_VT_DOUBLE = 8,\nADI_VT_STRING = 9,\nADI_VT_PCHAR = 10,\nADI_VT_BINARY = 11,\nADI_VT_PBYTE = 12,\nADI_VT_ENUM = 13',
        `special` INT(3) NOT NULL COMMENT 'Nothing = 0,\nCalculated = 1,\nOptionList = 2,\nDerivedDepth = 4,\nDateFormat = 8,\nWaveForm = 16,\nEnumList = 32,\nBoundArray = 64,\nVectorData = 256',
        `options_lists_id` INT NULL,
        `size` INT(5) NOT NULL,
        `number_of_elements` INT(5) NOT NULL,
        `number_of_decimals` INT(5) NOT NULL,
        `mnemonic32` VARCHAR(45) NULL,
        PRIMARY KEY (`id`),
        INDEX `fk_variables_unit_types1_idx` (`unit_types_id` ASC) VISIBLE,
        INDEX `fk_variables_variables_types1_idx` (`variables_types_id` ASC) VISIBLE,
        INDEX `fk_variables_options_lists1_idx` (`options_lists_id` ASC) VISIBLE,
        CONSTRAINT `fk_variables_unit_types1`
            FOREIGN KEY (`unit_types_id`)
            REFERENCES `mydb`.`unit_types` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION,
        CONSTRAINT `fk_variables_variables_types1`
            FOREIGN KEY (`variables_types_id`)
            REFERENCES `mydb`.`variables_types` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION,
        CONSTRAINT `fk_variables_options_lists1`
            FOREIGN KEY (`options_lists_id`)
            REFERENCES `mydb`.`options_lists` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION)
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`algorithms_calculation`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`algorithms_calculation` (
        `id` INT(5) NOT NULL,
        `name` VARCHAR(45) NOT NULL,
        PRIMARY KEY (`id`))
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`records_variables`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`records_variables` (
        `id` INT(5) NOT NULL AUTO_INCREMENT,
        `records_id` INT(5) NOT NULL,
        `variables_id` INT(5) NOT NULL,
        `calculated` TINYINT(1) NOT NULL COMMENT '0=variable stored in record, 1=calculated',
        `mnemonic` VARCHAR(4) NULL,
        `curve_label` VARCHAR(45) NULL,
        `mnemonic32` VARCHAR(45) NULL,
        `algorithms_calculation_id` INT(5) NULL,
        `reference_variable_id` INT(5) NULL,
        `coeff1` DOUBLE NOT NULL,
        `coeff2` DOUBLE NOT NULL,
        `coeff3` DOUBLE NOT NULL,
        PRIMARY KEY (`id`),
        INDEX `fk_records_variables_records1_idx` (`records_id` ASC) VISIBLE,
        INDEX `fk_records_variables_variables1_idx` (`variables_id` ASC) VISIBLE,
        INDEX `fk_records_variables_algorithms_calculation1_idx` (`algorithms_calculation_id` ASC) VISIBLE,
        INDEX `fk_records_variables_variables2_idx` (`reference_variable_id` ASC) VISIBLE,
        CONSTRAINT `fk_records_variables_records1`
            FOREIGN KEY (`records_id`)
            REFERENCES `mydb`.`records` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION,
        CONSTRAINT `fk_records_variables_variables1`
            FOREIGN KEY (`variables_id`)
            REFERENCES `mydb`.`variables` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION,
        CONSTRAINT `fk_records_variables_algorithms_calculation1`
            FOREIGN KEY (`algorithms_calculation_id`)
            REFERENCES `mydb`.`algorithms_calculation` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION,
        CONSTRAINT `fk_records_variables_variables2`
            FOREIGN KEY (`reference_variable_id`)
            REFERENCES `mydb`.`variables` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION)
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`data_tables`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`data_tables` (
        `wells_id` INT(5) NOT NULL,
        `runs_id` INT(5) NOT NULL,
        `records_id` INT(5) NOT NULL,
        `description` VARCHAR(45) NOT NULL,
        `table_number` INT(5) NOT NULL AUTO_INCREMENT,
        PRIMARY KEY (`wells_id`, `runs_id`, `records_id`, `description`),
        KEY `table_number` (`table_number`),
        INDEX `fk_data_runs1_idx` (`runs_id` ASC) VISIBLE,
        INDEX `fk_data_records1_idx` (`records_id` ASC) VISIBLE,
        UNIQUE INDEX `table_number_UNIQUE` (`table_number` ASC) VISIBLE,
        CONSTRAINT `fk_data_wells1`
            FOREIGN KEY (`wells_id`)
            REFERENCES `mydb`.`wells` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION,
        CONSTRAINT `fk_data_runs1`
            FOREIGN KEY (`runs_id`)
            REFERENCES `mydb`.`runs` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION,
        CONSTRAINT `fk_data_records1`
            FOREIGN KEY (`records_id`)
            REFERENCES `mydb`.`records` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION)
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`variables_vector_types`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`variables_vector_types` (
        `id` INT(5) NOT NULL,
        `name` VARCHAR(45) NOT NULL,
        PRIMARY KEY (`id`))
        ENGINE = InnoDB
        COMMENT = 'Unknown = 0\nUnsignedByteId = 1\nUnsignedShortId = 2\nUnsignedIntId = 3\nByteId = 4\nShortId = 5\nIntId = 6\nFloatId = 7\nDoubleId = 8';


        -- -----------------------------------------------------
        -- Table `mydb`.`variables_vector_attributes`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`variables_vector_attributes` (
        `wells_id` INT(5) NOT NULL,
        `runs_id` INT(5) NOT NULL,
        `records_id` INT(5) NOT NULL,
        `description` VARCHAR(45) NOT NULL,
        `variables_id` INT(5) NOT NULL,
        `variables_vector_types_id` INT(5) NOT NULL,
        `unit_types_id` INT(5) NOT NULL,
        `bin_start` DOUBLE NOT NULL,
        `bin_end` DOUBLE NOT NULL,
        PRIMARY KEY (`wells_id`, `runs_id`, `records_id`, `description`, `variables_id`),
        INDEX `fk_variables_vector_attributes_unit_types1_idx` (`unit_types_id` ASC) VISIBLE,
        INDEX `fk_variables_vector_attributes_variables_vector_types1_idx` (`variables_vector_types_id` ASC) VISIBLE,
        INDEX `fk_variables_vector_attributes_data_tables1_idx` (`wells_id` ASC, `runs_id` ASC, `records_id` ASC, `description` ASC) VISIBLE,
        CONSTRAINT `fk_variables_vector_attributes_variables1`
            FOREIGN KEY (`variables_id`)
            REFERENCES `mydb`.`variables` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION,
        CONSTRAINT `fk_variables_vector_attributes_unit_types1`
            FOREIGN KEY (`unit_types_id`)
            REFERENCES `mydb`.`unit_types` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION,
        CONSTRAINT `fk_variables_vector_attributes_variables_vector_types1`
            FOREIGN KEY (`variables_vector_types_id`)
            REFERENCES `mydb`.`variables_vector_types` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION,
        CONSTRAINT `fk_variables_vector_attributes_data_tables1`
            FOREIGN KEY (`wells_id` , `runs_id` , `records_id` , `description`)
            REFERENCES `mydb`.`data_tables` (`wells_id` , `runs_id` , `records_id` , `description`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION)
        ENGINE = InnoDB;


        -- -----------------------------------------------------
        -- Table `mydb`.`current_job`
        -- -----------------------------------------------------
        CREATE TABLE IF NOT EXISTS `mydb`.`current_job` (
        `id` INT(1) NOT NULL DEFAULT 1,
        `runs_id` INT(5) NOT NULL,
        `activity` INT(5) NOT NULL DEFAULT 0,
        `bit_depth` DOUBLE NOT NULL,
        `hole_depth` DOUBLE NOT NULL,
        `drill_model_desc` VARCHAR(45) NULL,
        `lithology_desc` VARCHAR(45) NULL,
        `survey_desc` VARCHAR(45) NULL,
        PRIMARY KEY (`id`),
        INDEX `fk_current_job_runs1_idx` (`runs_id` ASC) VISIBLE,
        CONSTRAINT `fk_current_job_runs1`
            FOREIGN KEY (`runs_id`)
            REFERENCES `mydb`.`runs` (`id`)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION)
        ENGINE = InnoDB;


        SET SQL_MODE=@OLD_SQL_MODE;
        SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
        SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
    """
    sql = sql.replace("`mydb`", f"`{db_name}`")
    # mycursor = conn.cursor()
    mycursor.execute(sql)
    # mycursor.close()
    
    
def PopulateFirstTables(mycursor, db_name):
    sql = f"""INSERT INTO `{db_name}`.`variables_types` (name, id) VALUES
        ('ADI_VT_NONE', 0), ('ADI_VT_CHAR', 1), ('ADI_VT_UCHAR', 2), ('ADI_VT_SHORT', 3),
        ('ADI_VT_USHORT', 4), ('ADI_VT_INT', 5), ('ADI_VT_UINT', 6),
        ('ADI_VT_FLOAT', 7), ('ADI_VT_DOUBLE', 8), ('ADI_VT_STRING', 9),
        ('ADI_VT_PCHAR', 10), ('ADI_VT_BINARY', 11), ('ADI_VT_PBYTE', 12), ('ADI_VT_ENUM', 13)"""
    mycursor.execute(sql)
    # conn.commit()

    sql = f"""INSERT INTO `{db_name}`.`variables_vector_types` (name, id) VALUES
        ('Unknown', 0), ('UnsignedByteId', 1), ('UnsignedShortId', 2), ('UnsignedIntId', 3),
        ('ByteId', 4), ('ShortId', 5), ('IntId', 6),
        ('FloatId', 7), ('DoubleId', 8)"""
    mycursor.execute(sql)
    # conn.commit()

    sql = f"""INSERT INTO `{db_name}`.`records_categories` (name, id) VALUES
        ('None', 0), ('Surface Logging', 1), ('MWD', 2)"""
    mycursor.execute(sql)
    # conn.commit()

    sql = f"""INSERT INTO `{db_name}`.`algorithms_calculation` (id, name) values (0, 'None'), (1, 'Bit Test'), (2, 'Reciprocal'), (3, 'Vector Access'), (4, 'Mod'), (5, 'Digit'), (6, 'Linear Equation')"""
    mycursor.execute(sql)
    
    sql = f"""INSERT INTO `{db_name}`.`records_types` (name, id) VALUES
        ('ADI_REC_UNKNOWN', 0), ('ADI_REC_NONE', 1), ('ADI_REC_TIME', 2), ('ADI_REC_DEPTH', 3),
        ('ADI_REC_TDA', 4), ('ADI_REC_LITH', 5), ('ADI_REC_TD', 6), ('ADI_REC_BHA_COMPONENT', 7),
        ('ADI_REC_BHA_COMPOSITE', 8), ('ADI_REC_DESCRIPTOR', 9), ('ADI_REC_PUMP', 10),
        ('ADI_REC_TIME_DEPTH', 11), ('ADI_REC_NO_INDEX', 12), ('ADI_REC_REMARKS', 13),
        ('ADI_REC_REALTIME', 14), ('ADI_REC_GEOMETRY', 15), ('ADI_REC_SURVEY', 16),
        ('ADI_REC_BAG', 17), ('ADI_REC_FAILURE', 18), ('ADI_REC_TOOL_PARAMS', 20),
        ('ADI_REC_ENVIRONMENTAL', 21), ('ADI_REC_WELL_RUN_INFO', 22), ('ADI_REC_LITH_PALETTE', 23),
        ('ADI_REC_DX_FILE', 24), ('ADI_REC_REPORT_EDITOR', 25), ('ADI_REC_AWC_EVENT_LOG', 26),
        ('ADI_REC_ATTACHMENT_MAN', 27), ('ADI_REC_WL_PARAMETER_EDITOR', 28), ('ADI_REC_MUD_EDITOR', 30),
        ('ADI_REC_RLE_COMPRESSION', 31), ('ADI_REC_BHA_ANALYSIS', 32), ('ADI_REC_SPERRY_IMAGE', 33),
        ('ADI_REC_TORQUE_DRAG', 34), ('ADI_REC_XMLREPORTVIEWER', 35), ('ADI_REC_PDT', 36),
        ('ADI_REC_IREMARKS', 37), ('ADI_REC_EVENT_LOG', 38), ('ADI_REC_VIBRATION_ANALYSIS', 39),
        ('ADI_REC_DXSERVERINFOVIEWER', 40), ('ADI_REC_GAS_SUMMARY', 41), ('ADI_REC_TRIP_SHEET', 42)"""
    mycursor.execute(sql)
    # conn.commit()
    
    
def PopulateWithData(mycursor, db_name):
    sql = f"INSERT INTO `{db_name}`.`measurement_classes` (name) VALUES (%s)"
    sql_sub = f"INSERT INTO `{db_name}`.`mc_units` (measurement_classes_id, name_long, name_short, function_type, arg1, arg2, psl_types) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    sql_upd = f"UPDATE `{db_name}`.`measurement_classes` SET mc_default_id=%s WHERE id=%s"
    for item in measurement_classes:
        val = (item.name,)
        mycursor.execute(sql, val)
        item.id = mycursor.lastrowid
        for sub_item in item.mc_units:
            val = (item.id, sub_item.name_long, sub_item.name_short,
                   sub_item.function_type, sub_item.arg1, sub_item.arg2, sub_item.psl_types)
            mycursor.execute(sql_sub, val)
            if sub_item.default:
                val = (mycursor.lastrowid, item.id)
                mycursor.execute(sql_upd, val)
    # conn.commit()

    unit_types.sort(key=lambda x: x.name)
    sql = "INSERT INTO `{db_name}`.`unit_types` (measurement_classes_id, name) VALUES (%s, %s)"
    for item in unit_types:
        val = (item.mc_parent.id, item.name)
        mycursor.execute(sql, val)
        item.id = mycursor.lastrowid
    # conn.commit()

    variables.sort(key=lambda x: x.name)
    sql = "INSERT INTO `{db_name}`.`variables` (name, mnemonic, curve_label, unit_types_id, variables_types_id, special, is_option_lists_read_only, size, number_of_elements, number_of_decimals, mnemonic32) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    sql_sub = "INSERT INTO `{db_name}`.`variables_option_lists` (variables_id, name) VALUES (%s, %s)"
    for item in variables:
        val = (item.name, item.mnemonic, item.curve_label, item.unit_type.id, item.var_type, item.special,
               item.is_option_list_read_only, item.size, item.number_of_elements, item.number_of_decimals, item.mnemonic32)
        mycursor.execute(sql, val)
        item.id = mycursor.lastrowid
        for sub_item in item.option_lists:
            val = (item.id, sub_item)
            mycursor.execute(sql_sub, val)
    # conn.commit()

    sql = "INSERT INTO `{db_name}`.`records_types` (id, name) VALUES (%s, %s)"
    for item in record_types:
        val = (item.id, item.name)
        mycursor.execute(sql, val)
    # conn.commit()

    sql = "INSERT INTO `{db_name}`.`records` (name, records_types_id, index_types, records_categories_id, primary_keys, psl_types, attributes) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    sql_sub = "INSERT INTO `{db_name}`.`records_variables` (records_id, variables_id, calculated, mnemonic, curve_label, mnemonic32, algorithms_calculation_id, reference_variable_id, coeff1, coeff2, coeff3) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    for item in records:
        val = (item.name, item.record_type_id, item.index_types,
               item.category_id, item.primary_keys, item.psl_types, item.attributes)
        mycursor.execute(sql, val)
        item.id = mycursor.lastrowid
        for sub_item in item.variables:
            var_ref_id = None
            if sub_item.var_ref != None: var_ref_id = sub_item.var_ref.id
            val = (item.id, sub_item.variable.id, sub_item.calculated, sub_item.mnemonic, sub_item.curve_label, sub_item.mnemonic32,
                   sub_item.algorithm, var_ref_id, sub_item.coeff1, sub_item.coeff2, sub_item.coeff3)
            mycursor.execute(sql_sub, val)
    # conn.commit()
    # mycursor.close()


def CreateDB(conn, db_name=None):
    print("Populating database...")
    start_time = time.time()

    mycursor = conn.cursor()
    mycursor.execute(f"CREATE DATABASE {db_name}")
    mycursor.execute(f"USE {db_name}")
    CreateTables(mycursor, db_name)
    PopulateFirstTables(mycursor, db_name)
    time.sleep(1)

    total_seconds = time.time() - start_time
    PrintTime(total_seconds)


if __name__ == "main":
    (host, user, pwd, db, txt) = GetCommandLineArgs()
    CheckIfDBExists()

    (measurement_classes, unit_types, variables,
    records, record_types) = ReadInputFile(txt)
    CreateDB(measurement_classes, unit_types, variables, records, record_types)
