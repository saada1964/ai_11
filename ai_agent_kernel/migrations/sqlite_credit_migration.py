"""
Migration مبسط لنظام الشحن مع SQLite للاختبار
Simple Credit System Migration with SQLite for Testing
"""

import sqlite3
import os
from datetime import datetime, timedelta
import secrets
import string


def create_sqlite_database():
    """إنشاء قاعدة بيانات SQLite للاختبار"""
    
    db_path = "credit_system_test.db"
    
    # إنشاء اتصال بقاعدة البيانات
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"🔄 إنشاء قاعدة بيانات SQLite: {db_path}")
    
    # إنشاء جدول أكواد الشحن
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            credit_amount INTEGER NOT NULL,
            discount_percentage REAL DEFAULT 0.0,
            max_uses INTEGER DEFAULT 1,
            current_uses INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            expires_at DATETIME,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # إنشاء جدول معاملات الشحن
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            credit_code_id INTEGER,
            transaction_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            amount_usd REAL DEFAULT 0.0,
            payment_method TEXT,
            payment_id TEXT,
            status TEXT DEFAULT 'pending',
            meta_dataTEXT DEFAULT '{}',
            processed_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (credit_code_id) REFERENCES credit_codes (id)
        )
    """)
    
    # إنشاء جدول طرق الدفع
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            provider TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            min_amount_usd REAL DEFAULT 1.0,
            max_amount_usd REAL DEFAULT 1000.0,
            supported_currencies TEXT DEFAULT '["USD"]',
            fees_percentage REAL DEFAULT 0.0,
            fixed_fee_usd REAL DEFAULT 0.0,
            meta_dataTEXT DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # إنشاء جدول سجل الدفعات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            credit_transaction_id INTEGER NOT NULL,
            payment_method_id INTEGER NOT NULL,
            external_payment_id TEXT,
            payment_intent_id TEXT,
            session_id TEXT,
            amount_usd REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            status TEXT DEFAULT 'pending',
            gateway_response TEXT DEFAULT '{}',
            webhook_data TEXT DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            FOREIGN KEY (credit_transaction_id) REFERENCES credit_transactions (id),
            FOREIGN KEY (payment_method_id) REFERENCES payment_methods (id)
        )
    """)
    
    # إنشاء جدول الاشتراكات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_name TEXT NOT NULL,
            monthly_credits INTEGER NOT NULL,
            monthly_price_usd REAL NOT NULL,
            payment_method_id INTEGER,
            status TEXT DEFAULT 'active',
            starts_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL,
            next_billing_date DATETIME,
            auto_renewal BOOLEAN DEFAULT 1,
            meta_dataTEXT DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (payment_method_id) REFERENCES payment_methods (id)
        )
    """)
    
    # إنشاء جدول المستخدمين (للاختبار)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            balance INTEGER DEFAULT 100000,
            is_active BOOLEAN DEFAULT 1,
            memory_profile TEXT DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # حفظ التغييرات وإغلاق الاتصال
    conn.commit()
    conn.close()
    
    print("✅ تم إنشاء جميع الجداول بنجاح")
    return db_path


def seed_test_data(db_path):
    """إدراج بيانات تجريبية"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔄 إدراج البيانات التجريبية...")
    
    # إدراج مستخدم اختبار
    cursor.execute("""
        INSERT OR REPLACE INTO users 
        (id, username, email, hashed_password, balance) 
        VALUES (1, 'test_user', 'test@example.com', 'hashed_password', 1000)
    """)
    
    cursor.execute("""
        INSERT OR REPLACE INTO users 
        (id, username, email, hashed_password, balance) 
        VALUES (2, 'admin_user', 'admin@example.com', 'hashed_password', 5000)
    """)
    
    # إدراج طرق الدفع
    payment_methods = [
        ("Stripe", "stripe", 1.0, 10000.0, '["USD", "EUR", "GBP"]', 2.9, 0.30),
        ("Plisio", "plisio", 0.50, 5000.0, '["USD", "EUR", "BTC", "ETH"]', 1.0, 0.10),
        ("PayPal", "paypal", 1.0, 6000.0, '["USD", "EUR", "GBP", "CAD"]', 2.9, 0.30)
    ]
    
    for method in payment_methods:
        cursor.execute("""
            INSERT OR REPLACE INTO payment_methods 
            (name, provider, min_amount_usd, max_amount_usd, supported_currencies, fees_percentage, fixed_fee_usd) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, method)
    
    # إدراج أكواد الشحن التجريبية
    sample_codes = [
        ("WELCOME100", "كود ترحيبي", "كود ترحيبي للمستخدمين الجدد", 1000, 0, 100, 30),
        ("BONUS500", "بونص 500 وحدة", "بونص خاص للمستخدمين المميزين", 500, 0, 50, 60),
        ("RESEARCH20", "خصم 20% على البحث", "خصم خاص على خدمات البحث المتقدمة", 200, 20, 25, 45),
        ("VIP1000", "كود VIP", "كود حصري للعملاء المميزين", 1000, 0, 10, 90)
    ]
    
    for code_data in sample_codes:
        # حساب تاريخ انتهاء الصلاحية
        expires_at = datetime.now() + timedelta(days=code_data[6])
        expires_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            INSERT OR REPLACE INTO credit_codes 
            (code, name, description, credit_amount, discount_percentage, max_uses, expires_at, created_by) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (*code_data[:6], expires_str, 2))  # created_by = 2 (admin_user)
    
    # إدراج معاملة تجريبية
    cursor.execute("""
        INSERT INTO credit_transactions 
        (user_id, credit_code_id, transaction_type, amount, status, created_at) 
        VALUES (1, 1, 'credit_code', 1000, 'completed', ?)
    """, (datetime.now(),))
    
    conn.commit()
    conn.close()
    
    print("✅ تم إدراج البيانات التجريبية بنجاح")


def create_indexes(db_path):
    """إنشاء فهارس قاعدة البيانات"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔄 إنشاء فهارس قاعدة البيانات...")
    
    # فهارس جدول أكواد الشحن
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_credit_codes_code ON credit_codes(code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_credit_codes_active ON credit_codes(is_active)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_credit_codes_expires ON credit_codes(expires_at)")
    
    # فهارس جدول معاملات الشحن
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_credit_transactions_user ON credit_transactions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_credit_transactions_status ON credit_transactions(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_credit_transactions_created ON credit_transactions(created_at)")
    
    # فهارس جدول سجل الدفعات
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_records_external ON payment_records(external_payment_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_records_status ON payment_records(status)")
    
    conn.commit()
    conn.close()
    
    print("✅ تم إنشاء الفهارس بنجاح")


def test_credit_system(db_path):
    """اختبار نظام الشحن"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔄 اختبار نظام الشحن...")
    
    # اختبار قراءة المستخدمين
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"✅ عدد المستخدمين: {user_count}")
    
    # اختبار قراءة أكواد الشحن
    cursor.execute("SELECT COUNT(*) FROM credit_codes")
    code_count = cursor.fetchone()[0]
    print(f"✅ عدد أكواد الشحن: {code_count}")
    
    # اختبار قراءة طرق الدفع
    cursor.execute("SELECT COUNT(*) FROM payment_methods")
    payment_count = cursor.fetchone()[0]
    print(f"✅ عدد طرق الدفع: {payment_count}")
    
    # اختبار قراءة المعاملات
    cursor.execute("SELECT COUNT(*) FROM credit_transactions")
    transaction_count = cursor.fetchone()[0]
    print(f"✅ عدد المعاملات: {transaction_count}")
    
    # اختبار استخدام كود شحن
    cursor.execute("SELECT code, credit_amount FROM credit_codes WHERE code = 'WELCOME100'")
    code = cursor.fetchone()
    if code:
        print(f"✅ كود الاختبار: {code[0]} - المبلغ: {code[1]} وحدة")
        
        # تحديث رصيد المستخدم
        cursor.execute("UPDATE users SET balance = balance + ? WHERE id = 1", (code[1],))
        
        # تسجيل المعاملة
        cursor.execute("""
            INSERT INTO credit_transactions 
            (user_id, credit_code_id, transaction_type, amount, status, created_at) 
            VALUES (?, ?, 'credit_code', ?, 'completed', ?)
        """, (1, 1, code[1], datetime.now()))
        
        # تحديث عدد استخدام الكود
        cursor.execute("UPDATE credit_codes SET current_uses = current_uses + 1 WHERE code = 'WELCOME100'")
        
        conn.commit()
        print(f"✅ تم استخدام الكود وإضافة {code[1]} وحدة للرصيد")
    
    # اختبار عرض قائمة أكواد الشحن النشطة
    cursor.execute("""
        SELECT code, name, credit_amount, current_uses, max_uses, expires_at 
        FROM credit_codes 
        WHERE is_active = 1
        ORDER BY created_at DESC
    """)
    
    active_codes = cursor.fetchall()
    print(f"\n📋 أكواد الشحن النشطة ({len(active_codes)}):")
    for code in active_codes:
        expires = code[5] if code[5] else "غير محدد"
        print(f"  - {code[0]}: {code[1]} ({code[2]} وحدة) - مستخدم {code[3]}/{code[4]} - ينتهي: {expires}")
    
    conn.close()


def run_sqlite_migration():
    """تشغيل migration SQLite الكامل"""
    
    print("🚀 بدء migration نظام الشحن مع SQLite...")
    print("=" * 50)
    
    try:
        # 1. إنشاء قاعدة البيانات والجداول
        db_path = create_sqlite_database()
        
        # 2. إدراج البيانات التجريبية
        seed_test_data(db_path)
        
        # 3. إنشاء الفهارس
        create_indexes(db_path)
        
        # 4. اختبار النظام
        test_credit_system(db_path)
        
        print("=" * 50)
        print("🎉 تم تشغيل migration نظام الشحن بنجاح!")
        print(f"\n📊 ملخص التحديثات:")
        print(f"  ✅ قاعدة البيانات: {db_path}")
        print(f"  ✅ 6 جداول تم إنشاؤها")
        print(f"  ✅ 3 طرق دفع تم إدراجها")
        print(f"  ✅ 4 أكواد شحن تم إنشاؤها")
        print(f"  ✅ مستخدمين تجريبيين تم إنشاؤهما")
        print(f"  ✅ فهارس قاعدة البيانات تم إنشاؤها")
        print(f"  ✅ النظام تم اختباره بنجاح")
        
        print(f"\n🔗 استخدم قاعدة البيانات: {db_path}")
        print(f"📱 يمكنك الآن:")
        print(f"  - استخدام أكواد الشحن: WELCOME100, BONUS500, RESEARCH20, VIP1000")
        print(f"  - شحن الرصيد عبر Stripe, Plisio, PayPal")
        print(f"  - تتبع المعاملات والاشتراكات")
        print(f"  - عرض الإحصائيات والتقارير")
        
    except Exception as e:
        print(f"❌ خطأ في migration نظام الشحن: {str(e)}")
        raise


if __name__ == "__main__":
    run_sqlite_migration()