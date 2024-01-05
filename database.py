import sqlite3
import os


def get_max_page_from_db(db_path:str, category:str):
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(f"SELECT MAX(page) FROM {category}")
    highest_page = cursor.fetchone()[0]
    conn.close()
    
    if highest_page == None:
        highest_page = 0
    
    return highest_page


def check_table_exists(db_path:str, category:str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{category}'")
    if cursor.fetchone():
        return True
    return False
    

def check_db_entry_exists(db_path:str, category:str, id_value=None, name=None):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if id_value == None and name != None:
        cursor.execute(f'SELECT * FROM {category} WHERE name = ?', (name,))
    elif id_value != None:
        cursor.execute(f'SELECT * FROM {category} WHERE id = ?', (id_value,))
    else:
        return False
    result = cursor.fetchone()  # Fetches the first row that matches the condition
    conn.close()

    # Check if the result is not None (entry exists) or None (entry does not exist)
    return result is not None

# Function to insert data into the database
def insert_or_update_entry(db_path:str, vid_id:str , name:str, category:str, page:int, download_date, url:str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if the entry exists
    cursor.execute(f'SELECT * FROM {category} WHERE vid_id = ?', (vid_id,))
    existing_entry = cursor.fetchone()

    if existing_entry:
        # If the entry exists, update it
        cursor.execute(f'''
            UPDATE {category}
            SET vid_id=?, name=?, category=?, page=?, download_date=?, url=?
            WHERE vid_id=?
        ''', (vid_id, name, category, page, download_date, url, vid_id))
    else:
        # If the entry does not exist, insert a new one
        cursor.execute(f'''
            INSERT INTO {category} (vid_id, name, category, page, download_date, url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (vid_id, name, category, page, download_date, url))
    conn.commit()
    conn.close()

# Function to create a new database if it doesn't exist
def create_new_db(db_path:str, category:str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {category} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vid_id TEXT,
            name TEXT,
            category TEXT,
            page INTEGER,
            download_date DATE,
            url TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
# Function to check if the database exists
def check_db_exists(db_path:str, category:str):
    if not os.path.exists(db_path):
        print("    - Database not found. Creating a new one...")
        create_new_db(db_path, category)
        print("    - Database created at", db_path)
    else:
        print("    - Database already exists at", db_path)
        if not check_table_exists(db_path, category):
            print(f"    - Table: {category} not found. Creating table ...")
            create_new_db(db_path, category)            
            print("    - Table created")
