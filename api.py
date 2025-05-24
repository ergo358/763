from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, add_request, list_requests, cancel_request

init_db()
app = FastAPI(title="Booking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/requests/{user_id}")
def api_list_requests(user_id: int):
    res = list_requests(user_id)
    return [{"id": r[0], "room": r[1], "date": r[2], "status": r[3]} for r in res]

@app.post("/api/requests/add")
def api_add_request(user_id: int, username: str, room: str, date: str):
    add_request(user_id, username, room, date)
    return {"detail": "ok"}

@app.post("/api/requests/cancel")
def api_cancel_request(user_id: int, request_id: int):
    cnt = cancel_request(request_id, user_id)
    if cnt:
        return {"detail": "cancelled"}
    raise HTTPException(404, "Not found")