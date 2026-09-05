import app.db.base

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_deal_route_contract_requires_authentication():
    client.cookies.clear()

    response = client.get("/deals/1")

    assert response.status_code == 401


if __name__ == "__main__":
    test_deal_route_contract_requires_authentication()
    print("===== PHASE 2M-D12 AUTH CONTRACT TEST PASS =====")
