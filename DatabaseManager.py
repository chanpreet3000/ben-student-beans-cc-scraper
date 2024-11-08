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

    def bulk_insert_coupon_codes(self, coupon_codes: List[CouponCode]) -> None:
        """
        Bulk insert or update coupon codes in the coupon_codes collection
        If a coupon code exists, update its expiry
        """
        try:
            operations = []
            for coupon in coupon_codes:
                operations.append(
                    UpdateOne(
                        {"code": coupon.code},
                        {"$set": coupon.to_dict()},
                        upsert=True
                    )
                )

            result = self.db[self.coupon_codes_collection].bulk_write(operations)
            Logger.info(
                f"Bulk insert/update completed. Inserted: {result.upserted_count}, Modified: {result.modified_count}")
        except PyMongoError as e:
            Logger.error("Failed to bulk insert/update coupon codes", e)
            raise

    def get_valid_coupon_codes(self) -> List[CouponCode]:
        """
        Return all coupon codes that are not expired
        """
        try:
            current_time = datetime.utcnow().isoformat()
            cursor = self.db[self.coupon_codes_collection].find(
                {"expiry": {"$gt": current_time}}
            )

            valid_coupons = []
            for doc in cursor:
                valid_coupons.append(CouponCode(
                    code=doc['code'],
                    expiry=doc['expiry'],
                    inserted_at=doc['inserted_at']
                ))

            Logger.info(f"Retrieved {len(valid_coupons)} valid & unique coupon codes")
            return valid_coupons
        except PyMongoError as e:
            Logger.error("Failed to fetch valid coupon codes", e)
            raise

    def close(self):
        """Close MongoDB connection when object is destroyed"""
        if self.client:
            self.client.close()
            Logger.info("MongoDB connection closed")