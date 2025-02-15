from database import SessionLocal
from models import RadioStation, StationStatus

def update_station():
    """Update station with ID 2 to be active"""
    try:
        # Create database session
        db = SessionLocal()
        
        # Get station with ID 2
        station = db.query(RadioStation).filter(RadioStation.id == 2).first()
        if not station:
            print("Station with ID 2 not found")
            return
        
        # Update station status
        station.is_active = True
        station.status = StationStatus.active
        
        # Commit changes
        db.commit()
        print(f"Station {station.name} updated successfully")
        
    except Exception as e:
        print(f"Error updating station: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    update_station() 