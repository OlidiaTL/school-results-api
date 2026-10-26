import pytest


@pytest.fixture()
def setup_data(client, admin_headers):
    """Two students and two subjects, created by an admin."""
    students = [
        client.post(
            "/students",
            json={"student_number": num, "first_name": first, "last_name": "Test", "form": 4},
            headers=admin_headers,
        ).json()["id"]
        for num, first in [("S1", "Rudo"), ("S2", "Kuda")]
    ]
    subjects = [
        client.post("/subjects", json={"code": code, "name": name}, headers=admin_headers).json()["id"]
        for code, name in [("CS", "Computer Science"), ("ACC", "Accounting")]
    ]
    return {"students": students, "subjects": subjects, "headers": admin_headers}


def _record(client, headers, student_id, subject_id, term, score):
    return client.post(
        "/results",
        json={
            "student_id": student_id,
            "subject_id": subject_id,
            "term": term,
            "score": score,
            "assessed_on": "2026-03-20",
        },
        headers=headers,
    )


def test_record_and_list_results(client, setup_data):
    s1, _ = setup_data["students"]
    cs, _ = setup_data["subjects"]
    headers = setup_data["headers"]

    response = _record(client, headers, s1, cs, "2026-T1", 72.5)
    assert response.status_code == 201
    assert response.json()["recorded_by_id"] is not None

    listed = client.get("/results", params={"student_id": s1}, headers=headers).json()
    assert len(listed) == 1 and listed[0]["score"] == 72.5


def test_duplicate_result_for_same_term_conflicts(client, setup_data):
    s1, _ = setup_data["students"]
    cs, _ = setup_data["subjects"]
    headers = setup_data["headers"]
    assert _record(client, headers, s1, cs, "2026-T1", 60).status_code == 201
    assert _record(client, headers, s1, cs, "2026-T1", 65).status_code == 409


@pytest.mark.parametrize("term,score", [("2026-T4", 50), ("26-T1", 50), ("2026-T1", 101), ("2026-T1", -1)])
def test_invalid_term_or_score_rejected(client, setup_data, term, score):
    s1, _ = setup_data["students"]
    cs, _ = setup_data["subjects"]
    assert _record(client, setup_data["headers"], s1, cs, term, score).status_code == 422


def test_unknown_student_returns_404(client, setup_data):
    cs, _ = setup_data["subjects"]
    assert _record(client, setup_data["headers"], 9999, cs, "2026-T1", 50).status_code == 404


def test_student_summary_averages_by_subject(client, setup_data):
    s1, _ = setup_data["students"]
    cs, acc = setup_data["subjects"]
    headers = setup_data["headers"]
    _record(client, headers, s1, cs, "2026-T1", 80)
    _record(client, headers, s1, cs, "2026-T2", 70)
    _record(client, headers, s1, acc, "2026-T1", 60)

    summary = client.get(f"/students/{s1}/summary", headers=headers).json()
    by_code = {s["subject_code"]: s for s in summary["subjects"]}
    assert by_code["CS"]["average_score"] == 75.0
    assert by_code["CS"]["assessments"] == 2
    assert by_code["ACC"]["average_score"] == 60.0
    assert summary["overall_average"] == 70.0


def test_at_risk_flags_low_scores_and_sharp_drops(client, setup_data):
    rudo, kuda = setup_data["students"]
    cs, acc = setup_data["subjects"]
    headers = setup_data["headers"]

    # Rudo: steady and strong -> not flagged
    for term, score in [("2026-T1", 78), ("2026-T2", 80)]:
        _record(client, headers, rudo, cs, term, score)

    # Kuda: averaged 72 in T1, falls to 58 in T2 (still above 50, but a 14-point drop)
    _record(client, headers, kuda, cs, "2026-T1", 74)
    _record(client, headers, kuda, acc, "2026-T1", 70)
    _record(client, headers, kuda, cs, "2026-T2", 60)
    _record(client, headers, kuda, acc, "2026-T2", 56)

    flagged = client.get("/results/at-risk", headers=headers).json()
    assert [s["student_id"] for s in flagged] == [kuda]
    kuda_flag = flagged[0]
    assert kuda_flag["latest_term"] == "2026-T2"
    assert kuda_flag["latest_average"] == 58.0
    assert kuda_flag["previous_average"] == 72.0
    assert kuda_flag["change"] == -14.0
    assert len(kuda_flag["reasons"]) == 1


def test_at_risk_single_term_below_threshold(client, setup_data):
    rudo, _ = setup_data["students"]
    cs, _ = setup_data["subjects"]
    headers = setup_data["headers"]
    _record(client, headers, rudo, cs, "2026-T1", 42)

    flagged = client.get("/results/at-risk", headers=headers).json()
    assert flagged[0]["student_id"] == rudo
    assert flagged[0]["previous_average"] is None


def test_at_risk_form_filter(client, setup_data):
    rudo, _ = setup_data["students"]
    cs, _ = setup_data["subjects"]
    headers = setup_data["headers"]
    _record(client, headers, rudo, cs, "2026-T1", 30)

    assert client.get("/results/at-risk", params={"form": 4}, headers=headers).json()
    assert client.get("/results/at-risk", params={"form": 2}, headers=headers).json() == []


def test_teacher_can_record_results(client, setup_data, db):
    # A teacher (not just an admin) is allowed to record results.
    from app.models import Role, User
    from app.security import hash_password

    db.add(User(email="t@example.com", full_name="T", role=Role.teacher, hashed_password=hash_password("password123")))
    db.commit()
    token = client.post("/auth/token", data={"username": "t@example.com", "password": "password123"}).json()[
        "access_token"
    ]

    s1, _ = setup_data["students"]
    cs, _ = setup_data["subjects"]
    response = _record(client, {"Authorization": f"Bearer {token}"}, s1, cs, "2026-T1", 55)
    assert response.status_code == 201
