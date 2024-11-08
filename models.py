from datetime import datetime


class CouponCode:
    def __init__(self, code: str, expiry: str, inserted_at: str = None):
        self.code = code
        self.expiry = expiry
        self.inserted_at = inserted_at or datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            'code': self.code,
            'expiry': self.expiry,
            'inserted_at': self.inserted_at
        }

    def __str__(self):
        return self.to_dict().__str__()

    def __repr__(self):
        return self.__str__()
