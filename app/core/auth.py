"""Authentication and authorization utilities."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.database import User, RefreshToken
from app.models.schemas import UserCreate, UserResponse, Token, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(user_id: UUID) -> str:
    """Create a JWT refresh token."""
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """Hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    """Create a new user."""
    # Check if user exists
    existing = await get_user_by_email(db, user_data.email)
    if existing:
        raise ValueError("Email already registered")

    existing = await get_user_by_username(db, user_data.username)
    if existing:
        raise ValueError("Username already taken")

    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """Authenticate a user."""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_tokens(user: User) -> Token:
    """Create access and refresh tokens for a user."""
    access_token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role.value})
    refresh_token = create_refresh_token(user.id)

    # Store refresh token
    async with AsyncSessionLocal() as db:
        token_hash = hash_token(refresh_token)
        expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        refresh_token_obj = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(refresh_token_obj)
        await db.commit()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def refresh_access_token(refresh_token: str) -> Optional[Token]:
    """Refresh an access token using a refresh token."""
    token_hash = hash_token(refresh_token)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.utcnow(),
            )
        )
        stored_token = result.scalar_one_or_none()

        if not stored_token:
            return None

        # Revoke old token
        stored_token.revoked = True

        # Get user
        user = await get_user_by_id(db, stored_token.user_id)
        if not user or not user.is_active:
            return None

        # Create new tokens
        new_access = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role.value})
        new_refresh = create_refresh_token(user.id)

        # Store new refresh token
        new_token_hash = hash_token(new_refresh)
        new_expires = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        new_token_obj = RefreshToken(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=new_expires,
        )
        db.add(new_token_obj)
        await db.commit()

    return Token(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def revoke_refresh_token(refresh_token: str) -> bool:
    """Revoke a refresh token."""
    token_hash = hash_token(refresh_token)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored_token = result.scalar_one_or_none()
        if stored_token:
            stored_token.revoked = True
            await db.commit()
            return True
    return False


async def get_current_user(db: AsyncSession, token: str) -> Optional[User]:
    """Get current user from token."""
    payload = decode_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        user = await get_user_by_id(db, UUID(user_id))
        return user if user and user.is_active else None
    except ValueError:
        return None


def require_role(allowed_roles: list[UserRole]):
    """Dependency factory for role-based access control."""
    async def role_checker(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker


# Add missing imports
from typing import Optional
from fastapi import Depends, HTTPException