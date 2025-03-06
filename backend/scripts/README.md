# SODAV Monitor Scripts

This directory contains utility scripts for the SODAV Monitor application.

## Available Scripts

### 1. Create Admin User
`create_admin_user.py` - Creates an admin user in the database.

**Usage:**
```bash
python create_admin_user.py [username] [email] [password]
```

If no arguments are provided, it will create a default admin user with:
- Username: admin
- Email: admin@sodav.sn
- Password: admin123

### 2. Fetch Senegalese Radio Stations
`fetch_senegal_stations.py` - Fetches radio stations from Senegal and adds them to the database.

**Usage:**
```bash
python fetch_senegal_stations.py
```

### 3. Test Music Detection
`test_music_detection.py` - Tests the music detection functionality on all radio stations in the database.

**Usage:**
```bash
python test_music_detection.py
```

## Running the Scripts

Make sure the backend server is running before executing these scripts. To run a script:

1. Navigate to the scripts directory:
```bash
cd backend/scripts
```

2. Execute the desired script:
```bash
python script_name.py
```

## Notes

- These scripts should be run from the `backend/scripts` directory to ensure proper path resolution.
- The scripts will automatically initialize the database if needed.
- Results from the music detection test will be saved to a JSON file in the current directory. 