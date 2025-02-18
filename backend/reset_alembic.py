from database import engine
from sqlalchemy import text
import os
import shutil

def reset_alembic():
    print("Resetting Alembic configuration...")
    
    # 1. Drop alembic_version table
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            conn.commit()
            print("✅ Dropped alembic_version table")
    except Exception as e:
        print(f"❌ Error dropping alembic_version table: {str(e)}")
        return False
    
    # 2. Clear versions directory
    versions_dir = os.path.join("migrations", "versions")
    try:
        if os.path.exists(versions_dir):
            for file in os.listdir(versions_dir):
                if file.endswith(".py"):
                    os.remove(os.path.join(versions_dir, file))
            print("✅ Cleared versions directory")
    except Exception as e:
        print(f"❌ Error clearing versions directory: {str(e)}")
        return False
    
    print("✅ Alembic configuration reset successfully")
    return True

if __name__ == "__main__":
    reset_alembic() 