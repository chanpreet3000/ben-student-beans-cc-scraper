import os
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database as MongoDatabase
from pymongo import UpdateOne
from pymongo.errors import DuplicateKeyError, PyMongoError
from Logger import Logger
from models import CouponCode

load_dotenv()


class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # Initialize database connection
        self.mongo_uri = os.getenv('MONGODB_URI')
        self.db_name = os.getenv('MONGODB_DB_NAME')
        if not self.mongo_uri or not self.db_name:
            raise ValueError("MongoDB URI not found in environment variables")

        self.client: Optional[MongoClient] = None
        self.db: Optional[MongoDatabase] = None

        # Collection names
        self.notification_channels_collection = 'notification_channels'
        self.coupon_codes_collection = 'coupon_codes'

        # Connect to database
        self._connect()

        # Create indexes
        self._create_indexes()

    def _connect(self) -> None:
        """Establish connection to MongoDB"""
        try:
            Logger.info("Connecting to MongoDB...")
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            self.client.server_info()  # Test connection
            Logger.info("Successfully connected to MongoDB")
        except PyMongoError as e:
            Logger.critical("Failed to connect to MongoDB", e)
            raise

    def _create_indexes(self) -> None:
        """Create necessary indexes for collections"""
        try:
            # Create unique index for channel_id
            self.db[self.notification_channels_collection].create_index(
                "channel_id", unique=True
            )
            self.db[self.coupon_codes_collection].create_index(
                "code", unique=True
            )
            Logger.info("Database indexes created successfully")
        except PyMongoError as e:
            Logger.error("Failed to create indexes", e)
            raise

    def add_discord_channel(self, channel_id: str) -> bool:
        """
        Add a Discord channel ID to notification_channels collection
        Returns True if successful, False if channel already exists
        """
        try:
            result = self.db[self.notification_channels_collection].insert_one({
                "channel_id": channel_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            Logger.info(f"Added Discord channel: {channel_id}")
            return True
        except DuplicateKeyError:
            Logger.warn(f"Discord channel already exists: {channel_id}")
            return False
        except PyMongoError as e:
            Logger.error(f"Failed to add Discord channel: {channel_id}", e)
            raise

    def remove_discord_channel(self, channel_id: str) -> bool:
        """
        Remove a Discord channel ID from notification_channels collection
        Returns True if successful, False if channel doesn't exist
        """
        try:
            result = self.db[self.notification_channels_collection].delete_one({
                "channel_id": channel_id
            })
            if result.deleted_count > 0:
                Logger.info(f"Removed Discord channel: {channel_id}")
                return True
            Logger.warn(f"Discord channel not found: {channel_id}")
            return False
        except PyMongoError as e:
            Logger.error(f"Failed to remove Discord channel: {channel_id}", e)
            raise

    def get_all_notification_channels(self) -> List[str]:
        """Return all channel IDs from notification_channels collection"""
        try:
            channels = self.db[self.notification_channels_collection].find({}, {"channel_id": 1, "_id": 0})
            return [channel["channel_id"] for channel in channels]
        except PyMongoError as e:
            Logger.error("Failed to fetch notification channels", e)
            raise

    def insert_or_update_coupon_code(self, coupon: CouponCode) -> None:
        """
        Insert a new coupon code or update an existing one
        """
        try:
            current_timestamp = datetime.utcnow().isoformat()
            # Check if the coupon code already exists
            existing_code = self.db[self.coupon_codes_collection].find_one({"code": coupon.code})
            if existing_code:
                # Update the existing coupon code
                self.db[self.coupon_codes_collection].update_one(
                    {"code": coupon.code},
                    {"$set": {
                        "updated_at": current_timestamp,
                    }}
                )
                Logger.info(f"Updated coupon code: {coupon.code}")
            else:
                # Insert a new coupon code
                self.db[self.coupon_codes_collection].insert_one({
                    "code": coupon.code,
                    "created_at": current_timestamp,
                    "updated_at": current_timestamp,
                    "used": False
                })
                Logger.info(f"Inserted new coupon code: {coupon.code}")
        except PyMongoError as e:
            Logger.error(f"Error inserting/updating coupon code: {coupon.code}", e)
            raise

    def bulk_insert_coupon_codes(self, coupon_codes: List[CouponCode]) -> None:
        """
        Serially insert or update coupon codes in the coupon_codes collection
        """
        if len(coupon_codes) == 0:
            Logger.warn("No coupon codes to insert")
            return
        try:
            for coupon in coupon_codes:
                self.insert_or_update_coupon_code(coupon)
        except PyMongoError as e:
            Logger.error("Failed to bulk insert/update coupon codes", e)
            raise

    def get_unused_coupon_codes(self, x: int) -> List[CouponCode]:
        """
        Return x unused coupon codes sorted by created_at (oldest first)
        """
        try:
            cursor = self.db[self.coupon_codes_collection].find(
                {"used": False},
                projection={"_id": 0},
                sort=[("created_at", 1)]
            ).limit(x)

            unused_coupons = []
            for doc in cursor:
                unused_coupons.append(CouponCode(
                    code=doc['code'],
                    created_at=doc['created_at'],
                    updated_at=doc['updated_at'],
                    used=doc['used']
                ))

            # mark the coupon codes as used
            self.mark_coupon_codes_as_used(unused_coupons)

            Logger.info(f"Retrieved {len(unused_coupons)} unused coupon codes")
            return unused_coupons
        except PyMongoError as e:
            Logger.error("Failed to fetch unused coupon codes", e)
            raise

    def mark_coupon_codes_as_used(self, coupon_codes: List[CouponCode]) -> None:
        """
        Mark a list of coupon codes as used in the database
        """
        if len(coupon_codes) == 0:
            Logger.warn("No coupon codes to mark as used")
            return
        try:
            operations = [
                UpdateOne(
                    {"code": coupon.code},
                    {"$set": {"used": True, "updated_at": datetime.utcnow().isoformat()}}
                )
                for coupon in coupon_codes
            ]
            result = self.db[self.coupon_codes_collection].bulk_write(operations)
            Logger.info(f"Marked {result.modified_count} coupon codes as used")
        except PyMongoError as e:
            Logger.error("Failed to mark coupon codes as used", e)
            raise

    def get_unused_coupon_codes_count(self) -> int:
        """
        Return the count of un-used coupon codes
        """
        try:
            unused_count = self.db[self.coupon_codes_collection].count_documents({"used": False})
            return unused_count
        except PyMongoError as e:
            Logger.error("Failed to get coupon codes count", e)
            raise

    def close(self):
        """Close MongoDB connection when object is destroyed"""
        if self.client:
            self.client.close()
            Logger.info("MongoDB connection closed")
