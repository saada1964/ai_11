from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from api.dependencies import authenticate_websocket_user, get_db # سنحتاج لإنشاء هذه
from models import User

router = APIRouter()

# ======================================================================
# مدير الاتصالات (لتتبع العملاء المتصلين)
# ======================================================================
class ConnectionManager:
    def __init__(self):
        # قاموس لتخزين الاتصالات لكل مستخدم
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_text(message)

    async def broadcast(self, message: str):
        for user_id, websocket in self.active_connections.items():
            await websocket.send_text(message)

manager = ConnectionManager()

# ======================================================================
# نقطة نهاية WebSocket الرئيسية
# ======================================================================
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...), # اجعل التوكن مطلوبًا كـ query parameter
    db: AsyncSession = Depends(get_db)
):
    """
    نقطة نهاية WebSocket للتواصل في الوقت الفعلي.
    تقوم بمصادقة المستخدم بناءً على التوكن.
    """
    # 1. مصادقة المستخدم
    user = await authenticate_websocket_user(token=token, db=db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    # 2. قبول الاتصال وربطه بالمستخدم
    await manager.connect(websocket, user_id=user.id)
    print(f"WebSocket connected for user: {user.username} (ID: {user.id})")
    
    try:
        # 3. حلقة الاستماع للرسائل من العميل
        while True:
            data = await websocket.receive_text()
            print(f"Message from user {user.id}: {data}")
            
            # يمكنك هنا توجيه الرسالة إلى المنسق أو أي منطق آخر
            # للرد، سنقوم فقط بإرسال رسالة تأكيد
            await manager.send_personal_message(f"Message received: {data}", user_id=user.id)
            
    except WebSocketDisconnect:
        manager.disconnect(user_id=user.id)
        print(f"WebSocket disconnected for user: {user.id}")