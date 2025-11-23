"""Tests for LLM model management API endpoints."""

import pytest
from fastapi import status

from app.core.security import create_access_token
from app.services.user_service import UserService


async def create_user_and_token(db_session, user_data):
    """Helper to register a user and generate auth headers."""
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


class TestLLMModelAPI:
    """Test suite for LLM model CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_and_get_llm_model(self, async_client, db_session, test_user_data):
        """Users can register an LLM model and fetch it."""
        _, headers = await create_user_and_token(db_session, test_user_data)
        payload = {
            "base_url": "https://models.example.com",
            "api_key": "sk-test",
            "model_endpoint_name": "gpt-4o",
            "model_name": "GPT-4o",
        }

        create_resp = await async_client.post(
            "/api/v1/llm-models",
            json=payload,
            headers=headers,
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        created = create_resp.json()
        assert created["base_url"] == payload["base_url"]
        assert "api_key" not in created

        get_resp = await async_client.get(
            f"/api/v1/llm-models/{created['id']}",
            headers=headers,
        )
        assert get_resp.status_code == status.HTTP_200_OK
        fetched = get_resp.json()
        assert fetched["id"] == created["id"]
        assert fetched["model_endpoint_name"] == payload["model_endpoint_name"]

    @pytest.mark.asyncio
    async def test_list_llm_models_scoped_to_user(
        self,
        async_client,
        db_session,
        test_user_data,
        test_user_data_2,
    ):
        """Ensure LLM model listings are per user."""
        _, headers_user1 = await create_user_and_token(db_session, test_user_data)
        _, headers_user2 = await create_user_and_token(db_session, test_user_data_2)

        payload_user1 = {
            "base_url": "https://api.user1.com",
            "api_key": "sk-u1",
            "model_endpoint_name": "u1-model",
            "model_name": "User 1 Model",
        }
        payload_user2 = {
            "base_url": "https://api.user2.com",
            "api_key": "sk-u2",
            "model_endpoint_name": "u2-model",
            "model_name": "User 2 Model",
        }

        await async_client.post(
            "/api/v1/llm-models",
            json=payload_user1,
            headers=headers_user1,
        )
        await async_client.post(
            "/api/v1/llm-models",
            json=payload_user2,
            headers=headers_user2,
        )

        list_resp = await async_client.get(
            "/api/v1/llm-models",
            headers=headers_user1,
        )
        assert list_resp.status_code == status.HTTP_200_OK
        data = list_resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["model_endpoint_name"] == payload_user1["model_endpoint_name"]

    @pytest.mark.asyncio
    async def test_update_llm_model(self, async_client, db_session, test_user_data):
        """Users can update mutable LLM fields."""
        _, headers = await create_user_and_token(db_session, test_user_data)
        payload = {
            "base_url": "https://api.example.com",
            "api_key": "sk-test",
            "model_endpoint_name": "claude-3",
            "model_name": "Claude 3",
        }
        create_resp = await async_client.post(
            "/api/v1/llm-models",
            json=payload,
            headers=headers,
        )
        llm_id = create_resp.json()["id"]

        update_resp = await async_client.put(
            f"/api/v1/llm-models/{llm_id}",
            json={"model_name": "Claude 3 Haiku", "api_key": "sk-new"},
            headers=headers,
        )
        assert update_resp.status_code == status.HTTP_200_OK
        updated = update_resp.json()
        assert updated["model_name"] == "Claude 3 Haiku"

    @pytest.mark.asyncio
    async def test_delete_llm_model(self, async_client, db_session, test_user_data):
        """Users can delete LLM models."""
        _, headers = await create_user_and_token(db_session, test_user_data)
        payload = {
            "base_url": "https://api.delete.com",
            "api_key": "sk-delete",
            "model_endpoint_name": "delete-me",
            "model_name": "Delete Me",
        }
        create_resp = await async_client.post(
            "/api/v1/llm-models",
            json=payload,
            headers=headers,
        )
        llm_id = create_resp.json()["id"]

        delete_resp = await async_client.delete(
            f"/api/v1/llm-models/{llm_id}",
            headers=headers,
        )
        assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

        get_resp = await async_client.get(
            f"/api/v1/llm-models/{llm_id}",
            headers=headers,
        )
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_unauthorized_llm_access_rejected(self, async_client):
        """Listing models without a token fails."""
        response = await async_client.get("/api/v1/llm-models")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

