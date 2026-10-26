def _student(number="S001", first="Tariro", last="Moyo", form=3, house="Baobab"):
    return {"student_number": number, "first_name": first, "last_name": last, "form": form, "house": house}


def test_admin_creates_and_reads_student(client, admin_headers):
    created = client.post("/students", json=_student(), headers=admin_headers)
    assert created.status_code == 201
    student_id = created.json()["id"]

    fetched = client.get(f"/students/{student_id}", headers=admin_headers)
    assert fetched.status_code == 200
    assert fetched.json()["last_name"] == "Moyo"


def test_teacher_cannot_create_student(client, teacher_headers):
    assert client.post("/students", json=_student(), headers=teacher_headers).status_code == 403


def test_form_must_be_between_1_and_6(client, admin_headers):
    assert client.post("/students", json=_student(form=7), headers=admin_headers).status_code == 422


def test_duplicate_student_number_conflicts(client, admin_headers):
    assert client.post("/students", json=_student(), headers=admin_headers).status_code == 201
    assert client.post("/students", json=_student(first="Other"), headers=admin_headers).status_code == 409


def test_list_filters_and_paginates(client, admin_headers):
    for i, (first, form) in enumerate([("Anesu", 1), ("Brian", 1), ("Chipo", 2)]):
        client.post(
            "/students", json=_student(number=f"S{i}", first=first, last=f"L{i}", form=form), headers=admin_headers
        )

    page = client.get("/students", params={"form": 1, "limit": 1}, headers=admin_headers).json()
    assert page["total"] == 2
    assert len(page["items"]) == 1

    found = client.get("/students", params={"search": "chip"}, headers=admin_headers).json()
    assert [s["first_name"] for s in found["items"]] == ["Chipo"]


def test_partial_update(client, admin_headers):
    student_id = client.post("/students", json=_student(), headers=admin_headers).json()["id"]
    response = client.patch(f"/students/{student_id}", json={"form": 4}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["form"] == 4
    assert response.json()["first_name"] == "Tariro"


def test_delete_then_404(client, admin_headers):
    student_id = client.post("/students", json=_student(), headers=admin_headers).json()["id"]
    assert client.delete(f"/students/{student_id}", headers=admin_headers).status_code == 204
    assert client.get(f"/students/{student_id}", headers=admin_headers).status_code == 404
