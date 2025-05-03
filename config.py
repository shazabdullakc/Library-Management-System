import os
from configparser import ConfigParser

def config(filename='database.ini', section='mysql'):
    # Create a parser
    parser = ConfigParser()
    
    # Check if config file exists, if not create with default values
    if not os.path.exists(filename):
        parser['mysql'] = {
            'host': 'localhost',
            'port': '3306',  # Default MySQL port
            'database': 'library_management',
            'user': 'root',
            'password': 'root'
        }
        with open(filename, 'w') as configfile:
            parser.write(configfile)
    
    # Read config file
    parser.read(filename)

    # Get section
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
            
        # Ensure port is an integer
        if 'port' in db:
            try:
                db['port'] = int(db['port'])
            except ValueError:
                raise Exception(f'Port must be a number in {filename}')
    else:
        raise Exception(f'Section {section} not found in the {filename} file')

    return db