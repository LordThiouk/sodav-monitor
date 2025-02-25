import sqlite3

def check_table_structure():
    conn = sqlite3.connect('sodav.db')
    cursor = conn.cursor()
    
    # Get table info
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='radio_stations';")
    table_info = cursor.fetchone()
    
    print("Radio Stations Table Structure:")
    print(table_info[0])
    
    conn.close()

if __name__ == "__main__":
    check_table_structure() 