"""
Migration لإضافة جداول نظام الشحن والدفع
Migration to add credit and payment system tables
"""

from sqlalchemy import text
from database.database import engine, Base
from models.credit_models import (
    CreditCode, CreditTransaction, PaymentMethod, 
    PaymentRecord, Subscription
)


def create_credit_system_tables():
    """إنشاء جداول نظام الشحن"""
    
    print("🔄 إنشاء جداول نظام الشحن...")
    
    # إنشاء الجداول
    CreditCode.__table__.create(bind=engine, checkfirst=True)
    print("✅ تم إنشاء جدول credit_codes")
    
    CreditTransaction.__table__.create(bind=engine, checkfirst=True)
    print("✅ تم إنشاء جدول credit_transactions")
    
    PaymentMethod.__table__.create(bind=engine, checkfirst=True)
    print("✅ تم إنشاء جدول payment_methods")
    
    PaymentRecord.__table__.create(bind=engine, checkfirst=True)
    print("✅ تم إنشاء جدول payment_records")
    
    Subscription.__table__.create(bind=engine, checkfirst=True)
    print("✅ تم إنشاء جدول subscriptions")
    
    print("🎉 تم إنشاء جميع جداول نظام الشحن بنجاح!")


def seed_payment_methods():
    """إدراج طرق الدفع الأساسية"""
    
    from sqlalchemy.orm import Session
    from models.credit_models import PaymentMethod
    
    print("🔄 إدراج طرق الدفع الأساسية...")
    
    with Session(engine) as db:
        # التحقق من وجود البيانات مسبقاً
        existing = db.query(PaymentMethod).count()
        if existing > 0:
            print("⚠️  طرق الدفع موجودة مسبقاً")
            return
        
        # إدراج Stripe
        stripe = PaymentMethod(
            name="Stripe",
            provider="stripe",
            min_amount_usd=1.00,
            max_amount_usd=10000.00,
            supported_currencies=["USD", "EUR", "GBP"],
            fees_percentage=2.9,
            fixed_fee_usd=0.30,
            meta_data={
                "webhook_url": "/webhooks/stripe",
                "supported_cards": ["visa", "mastercard", "amex", "discover"]
            }
        )
        
        # إدراج Plisio
        plisio = PaymentMethod(
            name="Plisio",
            provider="plisio",
            min_amount_usd=0.50,
            max_amount_usd=5000.00,
            supported_currencies=["USD", "EUR", "BTC", "ETH"],
            fees_percentage=1.0,
            fixed_fee_usd=0.10,
            meta_data={
                "webhook_url": "/webhooks/plisio",
                "supported_crypto": ["BTC", "ETH", "LTC", "BCH", "USDT"]
            }
        )
        
        # إدراج PayPal
        paypal = PaymentMethod(
            name="PayPal",
            provider="paypal",
            min_amount_usd=1.00,
            max_amount_usd=6000.00,
            supported_currencies=["USD", "EUR", "GBP", "CAD"],
            fees_percentage=2.9,
            fixed_fee_usd=0.30,
            meta_data={
                "webhook_url": "/webhooks/paypal",
                "sandbox_mode": True
            }
        )
        
        db.add_all([stripe, plisio, paypal])
        db.commit()
        
        print("✅ تم إدراج طرق الدفع الأساسية:")
        print("  - Stripe (بطاقات ائتمانية)")
        print("  - Plisio (عملات رقمية)")
        print("  - PayPal")


def create_sample_credit_codes():
    """إنشاء أكواد شحن تجريبية"""
    
    from sqlalchemy.orm import Session
    from models.credit_models import CreditCode
    
    print("🔄 إنشاء أكواد شحن تجريبية...")
    
    with Session(engine) as db:
        # التحقق من وجود أكواد مسبقاً
        existing = db.query(CreditCode).count()
        if existing > 0:
            print("⚠️  أكواد الشحن موجودة مسبقاً")
            return
        
        # أكواد تجريبية
        sample_codes = [
            {
                "code": "WELCOME100",
                "name": "كود ترحيبي",
                "description": "كود ترحيبي للمستخدمين الجدد",
                "credit_amount": 1000,
                "discount_percentage": 0.0,
                "max_uses": 100,
                "expires_days": 30
            },
            {
                "code": "BONUS500",
                "name": "بونص 500 وحدة",
                "description": "بونص خاص للمستخدمين المميزين",
                "credit_amount": 500,
                "discount_percentage": 0.0,
                "max_uses": 50,
                "expires_days": 60
            },
            {
                "code": "RESEARCH20",
                "name": "خصم 20% على البحث",
                "description": "خصم خاص على خدمات البحث المتقدمة",
                "credit_amount": 200,
                "discount_percentage": 20.0,
                "max_uses": 25,
                "expires_days": 45
            },
            {
                "code": "VIP1000",
                "name": "كود VIP",
                "description": "كود حصري للعملاء المميزين",
                "credit_amount": 1000,
                "discount_percentage": 0.0,
                "max_uses": 10,
                "expires_days": 90
            }
        ]
        
        # تحديث أكواد عشوائية
        import secrets
        import string
        
        for code_data in sample_codes:
            # إنشاء كود عشوائي إذا لم يتم تحديده
            if "code" not in code_data or not code_data["code"]:
                alphabet = string.ascii_uppercase + string.digits
                code_data["code"] = ''.join(secrets.choice(alphabet) for _ in range(8))
            
            # تحديد تاريخ انتهاء الصلاحية
            expires_at = None
            if code_data.get("expires_days"):
                from datetime import datetime, timedelta
                expires_at = datetime.utcnow() + timedelta(days=code_data["expires_days"])
                del code_data["expires_days"]  # إزالة من البيانات الأساسية
            
            credit_code = CreditCode(
                expires_at=expires_at,
                **code_data
            )
            db.add(credit_code)
        
        db.commit()
        
        print("✅ تم إنشاء أكواد الشحن التجريبية:")
        for code_data in sample_codes:
            print(f"  - {code_data['code']}: {code_data['credit_amount']} وحدة")


def update_user_balances():
    """تحديث أرصدة المستخدمين الحالية"""
    
    from sqlalchemy.orm import Session
    from models.models import User
    
    print("🔄 تحديث أرصدة المستخدمين...")
    
    with Session(engine) as db:
        # الحصول على جميع المستخدمين
        users = db.query(User).all()
        
        for user in users:
            # إذا كان رصيد المستخدم 0 أو أقل، أعطيه رصيد ابتدائي
            if user.balance <= 0:
                user.balance = 1000  # 1000 وحدة ابتدائية
                print(f"✅ تم تحديث رصيد المستخدم {user.username} إلى 1000 وحدة")
        
        db.commit()
        print(f"✅ تم تحديث أرصدة {len(users)} مستخدم")


def create_database_indexes():
    """إنشاء فهارس قاعدة البيانات لتحسين الأداء"""
    
    print("🔄 إنشاء فهارس قاعدة البيانات...")
    
    with engine.connect() as conn:
        # فهارس جدول أكواد الشحن
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_credit_codes_code 
            ON credit_codes(code);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_credit_codes_active_expires 
            ON credit_codes(is_active, expires_at);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_credit_codes_created_by 
            ON credit_codes(created_by);
        """))
        
        # فهارس جدول معاملات الشحن
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id 
            ON credit_transactions(user_id);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_credit_transactions_status 
            ON credit_transactions(status);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at 
            ON credit_transactions(created_at);
        """))
        
        # فهارس جدول سجل الدفعات
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_payment_records_external_id 
            ON payment_records(external_payment_id);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_payment_records_status 
            ON payment_records(status);
        """))
        
        conn.commit()
        print("✅ تم إنشاء جميع الفهارس بنجاح")


def run_credit_migration():
    """تشغيل migration نظام الشحن بالكامل"""
    
    print("🚀 بدء migration نظام الشحن والدفع...")
    print("=" * 50)
    
    try:
        # 1. إنشاء الجداول
        create_credit_system_tables()
        
        # 2. إدراج طرق الدفع الأساسية
        seed_payment_methods()
        
        # 3. إنشاء أكواد تجريبية
        create_sample_credit_codes()
        
        # 4. تحديث أرصدة المستخدمين
        update_user_balances()
        
        # 5. إنشاء الفهارس
        create_database_indexes()
        
        print("=" * 50)
        print("🎉 تم تشغيل migration نظام الشحن بنجاح!")
        print("\n📊 ملخص التحديثات:")
        print("  ✅ 5 جداول جديدة تم إنشاؤها")
        print("  ✅ 3 طرق دفع أساسية تم إدراجها")
        print("  ✅ 4 أكواد شحن تجريبية تم إنشاؤها")
        print("  ✅ أرصدة المستخدمين تم تحديثها")
        print("  ✅ فهارس قاعدة البيانات تم إنشاؤها")
        
        print("\n🔗 نقاط النهاية الجديدة:")
        print("  POST /credit/codes - إنشاء كود شحن")
        print("  POST /credit/codes/redeem - استخدام كود شحن")
        print("  GET /credit/codes - قائمة أكواد الشحن")
        print("  GET /credit/statistics - إحصائيات النظام")
        print("  GET /credit/transactions - معاملات المستخدم")
        print("  POST /credit/payments/initialize - بدء عملية دفع")
        print("  POST /credit/payments/complete - إتمام عملية دفع")
        print("  GET /credit/balance/{user_id} - رصيد المستخدم")
        print("  POST /credit/balance/topup - شحن الرصيد")
        
    except Exception as e:
        print(f"❌ خطأ في migration نظام الشحن: {str(e)}")
        raise


if __name__ == "__main__":
    run_credit_migration()