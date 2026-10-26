
import logging
import os
from uuid import UUID

import httpx
import psycopg
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import get_connection

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")

    if not supabase_url or not publishable_key:
        raise HTTPException(
            status_code=500,
            detail="Authentication is not configured on the server.",
        )

    try:
        response = httpx.get(
            f"{supabase_url}/auth/v1/user",
            headers={
                "apikey": publishable_key,
                "Authorization": f"Bearer {credentials.credentials}",
            },
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        logger.warning("Supabase Auth request failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Authentication service is temporarily unavailable.",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        auth_user = response.json()
        supabase_user_id = UUID(auth_user["id"])
        email = auth_user.get("email")

        if not isinstance(email, str) or not email.strip():
            raise ValueError("Authenticated user has no email.")

        email = email.strip().lower()

    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid authenticated user information.",
        )

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Reuse an existing mapping, if one exists.
                cur.execute(
                    """
                    SELECT id, email
                    FROM public.users
                    WHERE supabase_user_id = %s
                    """,
                    (supabase_user_id,),
                )
                row = cur.fetchone()

                if row is not None:
                    return {
                        "id": row[0],
                        "supabase_user_id": str(supabase_user_id),
                        "email": row[1],
                    }

                # Never attach an unmapped legacy account by email alone.
                cur.execute(
                    """
                    SELECT id
                    FROM public.users
                    WHERE LOWER(TRIM(email)) = %s
                    """,
                    (email,),
                )

                if cur.fetchone() is not None:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "This email matches an existing trading account. "
                            "Manual account linking is required."
                        ),
                    )

                # Provision a new internal account for this verified identity.
                cur.execute(
                    """
                    INSERT INTO public.users (email, supabase_user_id)
                    VALUES (%s, %s)
                    ON CONFLICT (supabase_user_id) DO NOTHING
                    RETURNING id, email
                    """,
                    (email, supabase_user_id),
                )
                row = cur.fetchone()

                if row is None:
                    # Another request may have created the mapping concurrently.
                    cur.execute(
                        """
                        SELECT id, email
                        FROM public.users
                        WHERE supabase_user_id = %s
                        """,
                        (supabase_user_id,),
                    )
                    row = cur.fetchone()

                if row is None:
                    raise HTTPException(
                        status_code=500,
                        detail="Unable to resolve the trading account.",
                    )

                return {
                    "id": row[0],
                    "supabase_user_id": str(supabase_user_id),
                    "email": row[1],
                }

    except HTTPException:
        raise
    except psycopg.Error as exc:
        logger.exception("Database error resolving authenticated user")

        if isinstance(exc, psycopg.errors.UniqueViolation):
            raise HTTPException(
                status_code=409,
                detail="Account conflict. Contact the administrator.",
            ) from exc

        raise HTTPException(
            status_code=500,
            detail="Unable to resolve the trading account.",
        ) from exc
