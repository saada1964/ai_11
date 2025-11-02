# نظام المصادقة والأمان الشامل - AI Agent Kernel

## نظرة عامة

تم تطوير نظام مصادقة وأمان شامل واحترافي للنظام الخلفي AI Agent Kernel. يوفر النظام حماية متقدمة ومصادقة قوية مع دعم الجلسات المتعددة والتواصل الفوري عبر WebSocket.

## الميزات الرئيسية

### 🔐 نظام المصادقة
- **JWT Authentication**: نظام مصادقة متقدم مع JSON Web Tokens
- **Access & Refresh Tokens**: 
  - Access tokens: مدة 30 دقيقة
  - Refresh tokens: مدة 7 أيام
- **تشفير قوي**: استخدام bcrypt مع 12 rounds لتشفير كلمات المرور
- **التحقق من قوة كلمة المرور**: متطلبات أمنية صارمة

### 👥 إدارة الجلسات
- **جلسات متعددة**: حتى 5 جلسات نشطة لكل مستخدم
- **تتبع الأجهزة**: معلومات الجهاز وموقع IP
- **إنهاء الجلسات**: إمكانية إنهاء جلسة واحدة أو جميع الجلسات
- **انتهاء صلاحية تلقائي**: تنظيف الجلسات المنتهية الصلاحية

### 🌐 WebSocket Server
- **التواصل الفوري**: دعم real-time communication
- **مصادقة WebSocket**: التحقق من الهوية لاتصالات WebSocket
- **إدارة الغرف**: دعم chat rooms والمجموعات
- **الإشعارات**: نظام إشعارات فوري للمستخدمين

### 🛡️ الحماية والأمان
- **Middleware متقدم**: حماية شاملة للطلبات
- **Rate Limiting**: الحماية من الهجمات
- **CORS محسن**: سياسة مشاركة الموارد الآمنة
- **Security Headers**: رؤوس أمنية معيارية

## البنية التقنية

### قاعدة البيانات
```sql
-- جدول active_sessions
CREATE TABLE active_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE NOT NULL,
    device_info JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### المكونات الرئيسية

#### 1. خدمات المصادقة (`services/auth_service.py`)
- `AuthService`: الخدمة الرئيسية للمصادقة
- تسجيل المستخدمين الجدد
- تسجيل الدخول والخروج
- إدارة الجلسات النشطة
- تغيير كلمات المرور

#### 2. الأدوات الأمنية (`utils/security.py`)
- `SecurityUtils`: أدوات التشفير والأمان
- `JWTManager`: إدارة JWT tokens
- تشفير كلمات المرور
- إنشاء وتحقق الـ tokens

#### 3. Middleware (`middleware/auth_middleware.py`)
- `AuthMiddleware`: الحماية العامة
- `RateLimitMiddleware`: الحماية من الهجمات
- `CORSMiddleware`: سياسة CORS محسنة

#### 4. WebSocket Server (`websockets/websocket_server.py`)
- `ConnectionManager`: إدارة اتصالات WebSocket
- `WebSocketHandler`: معالجة الرسائل
- دعم الغرف والإشعارات

#### 5. API Endpoints (`api/endpoints/auth.py`)
- `/auth/register`: تسجيل مستخدم جديد
- `/auth/login`: تسجيل الدخول
- `/auth/refresh`: تجديد الـ token
- `/auth/logout`: تسجيل الخروج
- `/auth/me`: معلومات المستخدم الحالي
- `/auth/sessions`: الجلسات النشطة
- `/auth/change-password`: تغيير كلمة المرور

## الإعداد والتشغيل

### 1. متطلبات النظام
```bash
pip install -r requirements.txt
```

### 2. متغيرات البيئة
```env
# في ملف .env
SECRET_KEY=your-ultra-secure-secret-key-for-jwt-tokens-minimum-32-characters-production
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ai_agent_kernel
REDIS_URL=redis://localhost:6379/0
```

### 3. إنشاء قاعدة البيانات
```bash
# تشغيل migration
python -m alembic upgrade head

# أو استخدام الـ migration المخصص
python migrations/001_add_active_sessions.py
```

### 4. تشغيل الخادم
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## استخدام النظام

### 1. تسجيل مستخدم جديد
```python
POST /auth/register
{
    "username": "user123",
    "email": "user@example.com", 
    "password": "SecurePassword123!"
}
```

### 2. تسجيل الدخول
```python
POST /auth/login
{
    "email": "user@example.com",
    "password": "SecurePassword123!"
}
```

### 3. استخدام WebSocket
```javascript
const token = "your-access-token";
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("Received:", data);
};

// إرسال رسالة
ws.send(JSON.stringify({
    type: "chat_message",
    room_id: "general",
    content: "مرحبا بالجميع!"
}));
```

### 4. حماية Endpoints
```python
from api.dependencies import get_current_active_user

@router.get("/protected")
async def protected_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    return {"message": f"مرحبا {current_user.username}"}
```

## الاختبارات

### تشغيل الاختبارات
```bash
pytest tests/test_auth_system.py -v
```

### الاختبارات المشمولة
- ✅ تشفير كلمات المرور
- ✅ إنشاء والتحقق من JWT tokens
- ✅ تسجيل المستخدمين
- ✅ المصادقة والجلسات
- ✅ API endpoints
- ✅ WebSocket authentication
- ✅ إدارة الجلسات المتعددة

## مراقبة الأمان

### Logs
```python
# مثال على logs الأمان
2024-01-01 12:00:00 INFO User authenticated: user@example.com
2024-01-01 12:01:00 WARNING JWT verification failed: Invalid token
2024-01-01 12:02:00 INFO Session 123 terminated for user 456
```

### Metrics
- عدد المستخدمين النشطين
- عدد الجلسات النشطة
- محاولات الدخول الفاشلة
- استخدام WebSocket

## إعدادات الأمان

### إعدادات إنتاج
```python
# في settings.py
SECRET_KEY = os.getenv("SECRET_KEY")  # من environment
DEBUG = False
ALLOWED_HOSTS = ["your-domain.com"]
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
MAX_SESSIONS_PER_USER = 5
PASSWORD_HASH_ROUNDS = 12
```

### SSL/TLS
```nginx
# إعداد Nginx للإنتاج
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## الخلاصة

تم تطوير نظام مصادقة وأمان شامل واحترافي يوفر:

✅ **الأمان**: تشفير متقدم وحماية شاملة
✅ **المرونة**: دعم الجلسات المتعددة والأجهزة المختلفة  
✅ **الأداء**: WebSocket للتواصل الفوري
✅ **القابلية للتوسع**: بنية قابلة للتطوير والصيانة
✅ **التوثيق**: توثيق شامل واختبارات كاملة

النظام جاهز للإنتاج ويوفر حماية عالية المستوى لتطبيق AI Agent Kernel.