from flask import Blueprint, jsonify, request

from services.ai_service import get_copilot_response


ai_bp = Blueprint("ai", __name__)


@ai_bp.get("/briefing")
def briefing():
    payload = get_copilot_response("")
    return jsonify(payload)


@ai_bp.post("/ask")
def ask():
    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()
    payload = get_copilot_response(question)
    return jsonify(payload)
