import sqlite3 as sq

with sq.connect("PC.db") as con:
    cur = con.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS pc (
    pc_name TEXT,
    os TEXT,
    processor TEXT,
    cores INTEGER,
    threads INTEGER,
    clock_frequency REAL,
    video_card_type TEXT,
    video_card_model TEXT,
    video_memory INTEGER,
    gpu TEXT,
    ram INTEGER,
    ram_type TEXT,
    bluetooth TEXT,
    wifi TEXT,
    network_adapter_speed REAL,
    ssd INTEGER,
    hdd INTEGER,
    rating REAL,
    link TEXT,
    price INTEGER,
    image BLOB
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS cpu (
    cpu_name TEXT,
    manufacturer TEXT,
    socket TEXT,
    cores INTEGER,
    threads INTEGER,
    clock_frequency REAL,
    temperature REAL,
    ram_type TEXT,
    max_ram INTEGER,
    ram_channels INTEGER,
    ram_freq REAL,
    graphics core TEXT,
    heat_gen INTEGER,
    energy REAL,
    rating REAL,
    link TEXT,
    price INTEGER,
    image BLOB
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS motherboard (
    motherboard_name TEXT,
    manufacturer TEXT,
    socket TEXT,
    chipset TEXT,
    form_factor TEXT,
    ram_type TEXT,
    ram_slots INTEGER,
    ram_channels INTEGER,
    ram_form TEXT,
    max_ram INTEGER,
    max_ram_freq REAL,
    pcie_v TEXT,
    sli_sup TEXT,
    m2_slots INTEGER,
    sata_ports INTEGER,
    network_adapter TEXT,
    network_adapter_speed REAL,
    bluetooth TEXT,
    cooler_power_connector TEXT,
    case_fan_power_connection_4pin INTEGER,
    main_power_connector INTEGER,
    cpu_power_connector TEXT,
    energy REAL,
    rating REAL,
    link TEXT,
    price INTEGER,
    image BLOB
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS gpu (
    gpu_name TEXT,
    manufacturer TEXT,
    purpose TEXT,
    length REAL,
    rtx TEXT,
    gpu TEXT,
    gpu_freq REAL,
    gpu_memory INTEGER,
    memory_type TEXT,
    bus_width INTEGER,
    con_interface TEXT,
    max_resolution TEXT,
    display_port TEXT,
    hdmi TEXT,
    add_power_pin INTEGER,
    energy REAL,
    rating REAL,
    link TEXT,
    price INTEGER,
    image BLOB
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS ram (
    ram_name TEXT,
    manufacturer TEXT,
    form_factor TEXT,
    ram_type TEXT,
    moduls_in_set INTEGER,
    amount INTEGER,
    clock_freq REAL,
    energy REAL,
    rating REAL,
    link TEXT,
    price INTEGER,
    image BLOB
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS psu (
    psu_name TEXT,
    manufacturer TEXT,
    form_factor TEXT,
    length REAL,
    power REAL,
    main_power_connector TEXT,
    cpu_power_connector TEXT,
    pcie_power_connector TEXT,
    molex_connector INTEGER,
    sata_connector INTEGER,
    certificate TEXT,
    rating REAL,
    link TEXT,
    price INTEGER,
    image BLOB
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS cooling_system (
    cs_name TEXT,
    manufacturer TEXT,
    type TEXT,
    construction_type TEXT,
    socket TEXT,
    heat_pipe INTEGER,
    power_dissipation REAL,
    height REAL,
    energy REAL,
    rating REAL,
    link TEXT,
    price INTEGER,
    image BLOB
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS storage(
    storage_name TEXT,
    manufacturer TEXT,
    storage_type TEXT,
    size TEXT,
    capacity INTEGER,
    spindle_speed REAL,
    max_data_transfer_rate REAL,
    connection_interface TEXT,
    energy REAL,
    rating REAL,
    link TEXT,
    price INTEGER,
    image BLOB
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS ssd(
    storage_name TEXT,
    manufacturer TEXT,
    size TEXT,
    capacity INTEGER,
    max_data_transfer_rate REAL,
    connection_interface TEXT,
    energy REAL,
    rating REAL,
    link TEXT,
    price INTEGER,
    image BLOB
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS cases(
    case_name TEXT,
    manufacturer TEXT,
    form_factor TEXT,
    motherboard_form TEXT,
    psu_form TEXT,
    psu_place TEXT,
    psu_length REAL,
    gpu_length REAL,
    cooler_height REAL,
    slots_25 INTEGER,
    slots_35 INTEGER,
    back_fan_size TEXT,
    back_fan_q INTEGER,
    front_fan_size TEXT,
    front_fan_q INTEGER,
    upper_fan_size TEXT,
    upper_fan_q INTEGER,
    down_fan_size TEXT,
    down_fan_q INTEGER,
    set_fans TEXT,
    lcs_sup TEXT,
    audio_jack INTEGER,
    micro_jack INTEGER,
    usb_2_0 INTEGER,
    usb_3_0 INTEGER,
    rating REAL,
    link TEXT,
    price INTEGER,
    image BLOB
    )""")

    cur.execute("""CREATE  TABLE IF NOT EXISTS pc_profiles (
    type TEXT,
    min_cpu_cores INTEGER,
    min_ram INTEGER,
    gpu_required BOOLEAN,
    min_ssd_gb INTEGER 
    )""")