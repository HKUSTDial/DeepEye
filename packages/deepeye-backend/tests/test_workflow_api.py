"""Tests for workflow API endpoints."""

import pytest
from fastapi import status

from app.core.security import create_access_token
from app.models.database.user import User
from app.services.user_service import UserService


class TestWorkflowAPI:
    """Test workflow API endpoints."""

    @pytest.mark.asyncio
    async def test_create_workflow_success(self, async_client, db_session, test_user_data):
        """Test successful workflow creation."""
        # Register and login user
        service = UserService()
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )
        token = create_access_token(data={"sub": user.id})

        # Create workflow
        workflow_data = {
            "name": "Test Workflow",
            "description": "A test workflow",
            "version": "1.0.0",
            "tags": ["test", "demo"],
            "workflow_data": {
                "workflow_id": "test-workflow-id",
                "metadata": {
                    "name": "Test Workflow",
                    "description": "A test workflow",
                    "version": "1.0.0",
                },
                "graph": {"nodes": [], "edges": []},
                "nodes": {},
            },
        }

        response = await async_client.post(
            "/api/v1/workflows",
            json=workflow_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == workflow_data["name"]
        assert data["description"] == workflow_data["description"]
        assert data["user_id"] == user.id
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_create_workflow_unauthorized(self, async_client):
        """Test creating workflow without authentication."""
        workflow_data = {
            "name": "Test Workflow",
            "workflow_data": {
                "workflow_id": "test-workflow-id",
                "metadata": {"name": "Test Workflow"},
                "graph": {"nodes": [], "edges": []},
                "nodes": {},
            },
        }

        response = await async_client.post(
            "/api/v1/workflows",
            json=workflow_data,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_list_workflows(self, async_client, db_session, test_user_data):
        """Test listing workflows."""
        # Register and login user
        service = UserService()
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )
        token = create_access_token(data={"sub": user.id})

        # Create a workflow
        workflow_data = {
            "name": "Test Workflow",
            "workflow_data": {
                "workflow_id": "test-workflow-id",
                "metadata": {"name": "Test Workflow"},
                "graph": {"nodes": [], "edges": []},
                "nodes": {},
            },
        }

        await async_client.post(
            "/api/v1/workflows",
            json=workflow_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        # List workflows
        response = await async_client.get(
            "/api/v1/workflows",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == workflow_data["name"]

    @pytest.mark.asyncio
    async def test_get_workflow_by_id(self, async_client, db_session, test_user_data):
        """Test getting workflow by ID."""
        # Register and login user
        service = UserService()
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )
        token = create_access_token(data={"sub": user.id})

        # Create a workflow
        workflow_data = {
            "name": "Test Workflow",
            "workflow_data": {
                "workflow_id": "test-workflow-id",
                "metadata": {"name": "Test Workflow"},
                "graph": {"nodes": [], "edges": []},
                "nodes": {},
            },
        }

        create_response = await async_client.post(
            "/api/v1/workflows",
            json=workflow_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        workflow_id = create_response.json()["id"]

        # Get workflow by ID
        response = await async_client.get(
            f"/api/v1/workflows/{workflow_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == workflow_id
        assert data["name"] == workflow_data["name"]

    @pytest.mark.asyncio
    async def test_get_workflow_not_found(self, async_client, db_session, test_user_data):
        """Test getting non-existent workflow."""
        # Register and login user
        service = UserService()
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )
        token = create_access_token(data={"sub": user.id})

        # Try to get non-existent workflow
        response = await async_client.get(
            "/api/v1/workflows/non-existent-id",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_workflow(self, async_client, db_session, test_user_data):
        """Test updating workflow."""
        # Register and login user
        service = UserService()
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )
        token = create_access_token(data={"sub": user.id})

        # Create a workflow
        workflow_data = {
            "name": "Test Workflow",
            "workflow_data": {
                "workflow_id": "test-workflow-id",
                "metadata": {"name": "Test Workflow"},
                "graph": {"nodes": [], "edges": []},
                "nodes": {},
            },
        }

        create_response = await async_client.post(
            "/api/v1/workflows",
            json=workflow_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        workflow_id = create_response.json()["id"]

        # Update workflow
        update_data = {
            "name": "Updated Workflow",
            "description": "Updated description",
        }

        response = await async_client.put(
            f"/api/v1/workflows/{workflow_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]

    @pytest.mark.asyncio
    async def test_delete_workflow(self, async_client, db_session, test_user_data):
        """Test deleting workflow."""
        # Register and login user
        service = UserService()
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )
        token = create_access_token(data={"sub": user.id})

        # Create a workflow
        workflow_data = {
            "name": "Test Workflow",
            "workflow_data": {
                "workflow_id": "test-workflow-id",
                "metadata": {"name": "Test Workflow"},
                "graph": {"nodes": [], "edges": []},
                "nodes": {},
            },
        }

        create_response = await async_client.post(
            "/api/v1/workflows",
            json=workflow_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        workflow_id = create_response.json()["id"]

        # Delete workflow
        response = await async_client.delete(
            f"/api/v1/workflows/{workflow_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify workflow is deleted
        get_response = await async_client.get(
            f"/api/v1/workflows/{workflow_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_workflow_isolation(self, async_client, db_session, test_user_data):
        """Test that users can only access their own workflows."""
        # Register two users
        service = UserService()
        user1 = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )
        user2 = await service.register_user(
            db=db_session,
            username="user2",
            email="user2@example.com",
            password="TestPassword123",
        )

        token1 = create_access_token(data={"sub": user1.id})
        token2 = create_access_token(data={"sub": user2.id})

        # User1 creates a workflow
        workflow_data = {
            "name": "User1 Workflow",
            "workflow_data": {
                "workflow_id": "test-workflow-id",
                "metadata": {"name": "User1 Workflow"},
                "graph": {"nodes": [], "edges": []},
                "nodes": {},
            },
        }

        create_response = await async_client.post(
            "/api/v1/workflows",
            json=workflow_data,
            headers={"Authorization": f"Bearer {token1}"},
        )
        workflow_id = create_response.json()["id"]

        # User2 tries to access User1's workflow
        response = await async_client.get(
            f"/api/v1/workflows/{workflow_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

