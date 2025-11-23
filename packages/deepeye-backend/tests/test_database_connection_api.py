"""Tests for database connection API endpoints."""

import pytest
from fastapi import status

from app.core.security import create_access_token
from app.services.user_service import UserService


async def create_user_and_token(db_session, user_data):
    """Helper to register a user and produce auth headers."""
    service = UserService()
    user = await service.register_user(
        db=db_session,
        username=user_data["username"],
        email=user_data["email"],
        password=user_data["password"],
        full_name=user_data.get("full_name"),
    )
    token = create_access_token(data={"sub": user.id})
    return user, {"Authorization": f"Bearer {token}"}


class TestDatabaseConnectionAPI:
    """Test suite for managing database connections."""

    @pytest.mark.asyncio
    async def test_create_and_get_connection(self, async_client, db_session, test_user_data):
        """Users can create a connection and retrieve it by ID."""
        _, headers = await create_user_and_token(db_session, test_user_data)
        payload = {
            "name": "Primary Warehouse",
            "type": "postgres",
            "host": "localhost",
            "port": 5432,
            "username": "postgres",
            "password": "secret",
            "database": "analytics",
        }

        create_resp = await async_client.post(
            "/api/v1/database-connections",
            json=payload,
            headers=headers,
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        created = create_resp.json()
        assert created["name"] == payload["name"]
        assert "password" not in created

        get_resp = await async_client.get(
            f"/api/v1/database-connections/{created['id']}",
            headers=headers,
        )
        assert get_resp.status_code == status.HTTP_200_OK
        fetched = get_resp.json()
        assert fetched["id"] == created["id"]
        assert fetched["host"] == payload["host"]

    @pytest.mark.asyncio
    async def test_list_connections_isolated_per_user(
        self,
        async_client,
        db_session,
        test_user_data,
        test_user_data_2,
    ):
        """Each user only sees their own connections."""
        _, headers_user1 = await create_user_and_token(db_session, test_user_data)
        _, headers_user2 = await create_user_and_token(db_session, test_user_data_2)

        payload_user1 = {
            "name": "User1 DB",
            "type": "mysql",
            "host": "u1.example.com",
            "port": 3306,
            "username": "u1",
            "password": "secret",
            "database": "db1",
        }
        payload_user2 = {
            "name": "User2 DB",
            "type": "postgres",
            "host": "u2.example.com",
            "port": 5432,
            "username": "u2",
            "password": "secret",
            "database": "db2",
        }

        await async_client.post(
            "/api/v1/database-connections",
            json=payload_user1,
            headers=headers_user1,
        )
        await async_client.post(
            "/api/v1/database-connections",
            json=payload_user2,
            headers=headers_user2,
        )

        list_resp = await async_client.get(
            "/api/v1/database-connections",
            headers=headers_user1,
        )
        assert list_resp.status_code == status.HTTP_200_OK
        data = list_resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == payload_user1["name"]

    @pytest.mark.asyncio
    async def test_update_connection(self, async_client, db_session, test_user_data):
        """Users can update mutable fields on a connection."""
        _, headers = await create_user_and_token(db_session, test_user_data)
        payload = {
            "name": "Data Lake",
            "type": "postgres",
            "host": "dl.example.com",
            "port": 5432,
            "username": "dl_user",
            "password": "secret",
            "database": "lake",
        }
        create_resp = await async_client.post(
            "/api/v1/database-connections",
            json=payload,
            headers=headers,
        )
        connection_id = create_resp.json()["id"]

        update_resp = await async_client.put(
            f"/api/v1/database-connections/{connection_id}",
            json={"name": "Updated Data Lake", "host": "updated.example.com"},
            headers=headers,
        )
        assert update_resp.status_code == status.HTTP_200_OK
        updated = update_resp.json()
        assert updated["name"] == "Updated Data Lake"
        assert updated["host"] == "updated.example.com"

    @pytest.mark.asyncio
    async def test_delete_connection(self, async_client, db_session, test_user_data):
        """Users can delete a connection they own."""
        _, headers = await create_user_and_token(db_session, test_user_data)
        payload = {
            "name": "Temp DB",
            "type": "sqlite",
            "host": "127.0.0.1",
            "port": 0,
            "username": "user",
            "password": "secret",
            "database": "tmp",
        }
        create_resp = await async_client.post(
            "/api/v1/database-connections",
            json=payload,
            headers=headers,
        )
        connection_id = create_resp.json()["id"]

        delete_resp = await async_client.delete(
            f"/api/v1/database-connections/{connection_id}",
            headers=headers,
        )
        assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

        get_resp = await async_client.get(
            f"/api/v1/database-connections/{connection_id}",
            headers=headers,
        )
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_unauthorized_access_rejected(self, async_client):
        """Endpoints require authentication."""
        response = await async_client.get("/api/v1/database-connections")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

