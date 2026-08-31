"""
User model and repository for the demo e-commerce project.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class User:
    """Represents a registered user in the system."""
    id: str
    email: str
    username: str
    hashed_password: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.email}>"


class UserRepository:
    """In-memory user repository (demo — swap with DB in production)."""

    def __init__(self):
        self._users: dict[str, User] = {}

    def save(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def find_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def find_by_email(self, email: str) -> Optional[User]:
        return next((u for u in self._users.values() if u.email == email), None)

    def find_all(self) -> List[User]:
        return list(self._users.values())

    def delete(self, user_id: str) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False
