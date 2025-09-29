"""Tests for the visa verification routes."""

import io

from app import db
from models import User, VisaDocument


def _upload_document(client, user_id, filename="passport.pdf"):
    data = {
        "user_id": str(user_id),
        "doc_type": "passport",
        "file": (io.BytesIO(b"dummy data"), filename),
    }
    response = client.post("/verify/documents", data=data, content_type="multipart/form-data")
    assert response.status_code == 201
    return response.get_json()["document"]


def test_upload_document_requires_file(client, user_id):
    response = client.post(
        "/verify/documents",
        data={"user_id": str(user_id), "doc_type": "passport"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "file" in response.get_data(as_text=True)


def test_upload_and_retrieve_document(client, user_id):
    document = _upload_document(client, user_id)

    list_response = client.get("/verify/documents", query_string={"user_id": user_id})
    assert list_response.status_code == 200
    documents = list_response.get_json()["documents"]
    assert len(documents) == 1
    assert documents[0]["id"] == document["id"]

    detail_response = client.get(f"/verify/documents/{document['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.get_json()["document"]
    assert detail["file_url"].endswith("passport.pdf")


def test_update_document_status_marks_user_verified(app_instance, client, user_id):
    document = _upload_document(client, user_id)

    update_response = client.patch(
        f"/verify/documents/{document['id']}",
        json={"status": "approved", "notes": "Looks good"},
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()["document"]
    assert updated["status"] == "approved"
    assert updated["notes"] == "Looks good"

    with app_instance.app_context():
        refreshed_user = db.session.get(User, user_id)
        assert refreshed_user.is_verified is True
        stored_document = db.session.get(VisaDocument, document["id"])
        assert stored_document.status == "approved"

    # Denying should flip the flag back to False
    deny_response = client.patch(
        f"/verify/documents/{document['id']}",
        json={"status": "denied"},
    )
    assert deny_response.status_code == 200

    with app_instance.app_context():
        refreshed_user = db.session.get(User, user_id)
        assert refreshed_user.is_verified is False
