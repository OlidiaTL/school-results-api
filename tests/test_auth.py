def test_login_with_wrong_password_is_rejected(client, admin_headers):
    response = client.post("/auth/token", data={"username": "admin@example.com", "password": "wrong-password"})
    assert response.status_code == 401


def test_me_returns_current_user(client, teacher_headers):
    response = client.get("/auth/me", headers=teacher_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "teacher"


def test_requests_without_token_are_rejected(client):
    assert client.get("/students").status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get("/students", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_admin_can_create_teacher(client, admin_headers):
    response = client.post(
        "/auth/users",
        json={"email": "new@example.com", "full_name": "New Teacher", "password": "password123"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["role"] == "teacher"


def test_teacher_cannot_create_users(client, teacher_headers):
    response = client.post(
        "/auth/users",
        json={"email": "x@example.com", "full_name": "X", "password": "password123"},
        headers=teacher_headers,
    )
    assert response.status_code == 403


def test_duplicate_email_conflicts(client, admin_headers):
    payload = {"email": "dup@example.com", "full_name": "Dup", "password": "password123"}
    assert client.post("/auth/users", json=payload, headers=admin_headers).status_code == 201
    assert client.post("/auth/users", json=payload, headers=admin_headers).status_code == 409
