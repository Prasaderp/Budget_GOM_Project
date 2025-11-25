"""
Script to initialize notification preferences for existing users.
Run this after migration to ensure all users have default preferences.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal
from src import models
from src.email_service import get_default_notification_preferences
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_user_preferences():
    db = SessionLocal()
    try:
        users = db.query(models.User).filter(
            models.User.notification_preferences.is_(None)
        ).all()
        
        if not users:
            logger.info("No users with NULL notification preferences found")
            return
        
        default_prefs = get_default_notification_preferences()
        updated_count = 0
        
        for user in users:
            user.notification_preferences = default_prefs
            updated_count += 1
        
        db.commit()
        logger.info(f"Initialized notification preferences for {updated_count} users")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error initializing user preferences: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_user_preferences()

