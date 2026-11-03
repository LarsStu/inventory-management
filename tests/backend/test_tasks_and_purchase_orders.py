"""
Tests for task and purchase order API endpoints.
"""
import pytest
import mock_data
import main


@pytest.fixture(autouse=True)
def reset_state():
    """Tasks and purchase orders live in shared module state, so reset them around each test."""
    main.tasks.clear()
    mock_data.purchase_orders.clear()
    yield
    main.tasks.clear()
    mock_data.purchase_orders.clear()


def po_payload(backlog_item_id="1", **overrides):
    payload = {
        "backlog_item_id": backlog_item_id,
        "supplier_name": "Acme Components",
        "quantity": 350,
        "unit_cost": 12.5,
        "expected_delivery_date": "2026-12-10",
        "notes": None,
    }
    payload.update(overrides)
    return payload


class TestTaskEndpoints:
    """Test suite for task endpoints."""

    def test_create_and_list_tasks(self, client):
        """Creating a task returns it as pending, and it appears in the list."""
        response = client.post("/api/tasks", json={"title": "Check stock", "priority": "high", "dueDate": "2026-12-01"})
        assert response.status_code == 201
        task = response.json()
        assert task["status"] == "pending"
        assert task["id"] >= 1001  # API ids stay clear of mock user task ids

        listed = client.get("/api/tasks").json()
        assert [t["id"] for t in listed] == [task["id"]]

    def test_create_task_rejects_blank_title(self, client):
        """A whitespace-only title is rejected with 400."""
        response = client.post("/api/tasks", json={"title": "   ", "priority": "low", "dueDate": "2026-12-01"})
        assert response.status_code == 400

    def test_create_task_rejects_invalid_date(self, client):
        """A due date that is not ISO 8601 is rejected with 400."""
        response = client.post("/api/tasks", json={"title": "Check", "priority": "low", "dueDate": "next week"})
        assert response.status_code == 400

    def test_list_is_newest_first(self, client):
        """Tasks are returned newest first."""
        first = client.post("/api/tasks", json={"title": "First", "priority": "low", "dueDate": "2026-12-01"}).json()
        second = client.post("/api/tasks", json={"title": "Second", "priority": "low", "dueDate": "2026-12-02"}).json()
        listed = client.get("/api/tasks").json()
        assert [t["id"] for t in listed] == [second["id"], first["id"]]

    def test_toggle_task_flips_status(self, client):
        """PATCH toggles pending and completed."""
        task = client.post("/api/tasks", json={"title": "Check", "priority": "low", "dueDate": "2026-12-01"}).json()
        toggled = client.patch(f"/api/tasks/{task['id']}")
        assert toggled.status_code == 200
        assert toggled.json()["status"] == "completed"
        assert client.patch(f"/api/tasks/{task['id']}").json()["status"] == "pending"

    def test_toggle_missing_task_returns_404(self, client):
        """Toggling an unknown task returns 404."""
        assert client.patch("/api/tasks/999999").status_code == 404

    def test_delete_task(self, client):
        """Deleting removes the task; deleting again returns 404."""
        task = client.post("/api/tasks", json={"title": "Check", "priority": "low", "dueDate": "2026-12-01"}).json()
        assert client.delete(f"/api/tasks/{task['id']}").status_code == 200
        assert client.get("/api/tasks").json() == []
        assert client.delete(f"/api/tasks/{task['id']}").status_code == 404


class TestPurchaseOrderEndpoints:
    """Test suite for purchase order endpoints."""

    def test_create_purchase_order_success(self, client):
        """A valid PO returns 201 and can be fetched by backlog item."""
        response = client.post("/api/purchase-orders", json=po_payload())
        assert response.status_code == 201
        po = response.json()
        assert po["backlog_item_id"] == "1"
        assert po["status"] == "Submitted"

        fetched = client.get("/api/purchase-orders/1")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == po["id"]

    def test_backlog_reports_purchase_order_id(self, client):
        """After a PO is created, the backlog item exposes its id so the dashboard shows View PO."""
        po = client.post("/api/purchase-orders", json=po_payload("1")).json()
        items = {item["id"]: item for item in client.get("/api/backlog").json()}
        assert items["1"]["has_purchase_order"] is True
        assert items["1"]["purchase_order_id"] == po["id"]
        assert items["2"]["purchase_order_id"] is None

    def test_duplicate_purchase_order_rejected(self, client):
        """Only one PO is allowed per backlog item."""
        client.post("/api/purchase-orders", json=po_payload("1"))
        assert client.post("/api/purchase-orders", json=po_payload("1")).status_code == 400

    def test_unknown_backlog_item_returns_404(self, client):
        """A PO for a backlog item that does not exist returns 404."""
        assert client.post("/api/purchase-orders", json=po_payload("999")).status_code == 404

    @pytest.mark.parametrize("overrides", [
        {"quantity": 0},
        {"unit_cost": -1},
        {"supplier_name": "  "},
        {"expected_delivery_date": "soon"},
    ])
    def test_invalid_purchase_order_rejected(self, client, overrides):
        """Non-positive quantity or cost, blank supplier, and bad dates return 400."""
        response = client.post("/api/purchase-orders", json=po_payload("2", **overrides))
        assert response.status_code == 400

    def test_get_purchase_order_missing_returns_404(self, client):
        """Fetching a PO for a backlog item without one returns 404."""
        assert client.get("/api/purchase-orders/2").status_code == 404
