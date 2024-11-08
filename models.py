from datetime import datetime


class CouponCode:
    def __init__(self, code: str, created_at: str = None, updated_at: str = None, used: bool = False):
        self.code = code
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or self.created_at
        self.used = used

    def to_dict(self):
        return {
            'code': self.code,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'used': self.used
        }

    def __str__(self):
        return self.to_dict().__str__()

    def __repr__(self):
        return self.__str__()
