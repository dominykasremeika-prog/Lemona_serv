import sqlite3

def add_telemetry_columns():
    conn = sqlite3.connect('instance/site.db')
    c = conn.cursor()
    
    columns = [
        ('last_ip', 'TEXT', '""'),
        ('last_ssid', 'TEXT', '""'),
        ('last_network_type', 'TEXT', '""'),
        ('last_refresh_rate', 'REAL', '0.0'),
        ('last_seen', 'REAL', '0.0')
    ]
    
    for col_name, col_type, default_val in columns:
        try:
            # Check if column exists first to avoid error spam
            c.execute(f"SELECT {col_name} FROM client_settings LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            try:
                c.execute(f"ALTER TABLE client_settings ADD COLUMN {col_name} {col_type} DEFAULT {default_val}")
                print(f"Added column {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"Column {col_name} already exists")
            
    conn.commit()
    conn.close()

if __name__ == '__main__':
    add_telemetry_columns()
