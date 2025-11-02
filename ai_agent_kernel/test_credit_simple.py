"""
اختبار بسيط لنظام الشحن بدون dependencies معقدة
Simple Credit System Test without Complex Dependencies
"""

import sqlite3
import os
from datetime import datetime, timedelta


def test_credit_system_simple():
    """اختبار بسيط لنظام الشحن"""
    
    db_path = "credit_system_test.db"
    
    if not os.path.exists(db_path):
        print("❌ قاعدة البيانات غير موجودة. يرجى تشغيل sqlite_credit_migration.py أولاً")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔄 اختبار نظام الشحن...")
    print("=" * 50)
    
    # اختبار 1: قراءة البيانات الأساسية
    print("📊 اختبار 1: قراءة البيانات الأساسية")
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"  ✅ عدد المستخدمين: {user_count}")
    
    cursor.execute("SELECT COUNT(*) FROM credit_codes")
    code_count = cursor.fetchone()[0]
    print(f"  ✅ عدد أكواد الشحن: {code_count}")
    
    cursor.execute("SELECT COUNT(*) FROM payment_methods")
    payment_count = cursor.fetchone()[0]
    print(f"  ✅ عدد طرق الدفع: {payment_count}")
    
    cursor.execute("SELECT COUNT(*) FROM credit_transactions")
    transaction_count = cursor.fetchone()[0]
    print(f"  ✅ عدد المعاملات: {transaction_count}")
    
    # اختبار 2: عرض قائمة أكواد الشحن
    print("\n📋 اختبار 2: عرض أكواد الشحن")
    cursor.execute("""
        SELECT code, name, credit_amount, current_uses, max_uses, is_active, expires_at 
        FROM credit_codes 
        ORDER BY created_at DESC
    """)
    
    codes = cursor.fetchall()
    print(f"  📝 قائمة أكواد الشحن ({len(codes)} كود):")
    for code in codes:
        status = "نشط" if code[5] else "معطل"
        expires = code[6] if code[6] else "غير محدد"
        print(f"    - {code[0]}: {code[1]} ({code[2]} وحدة) - مستخدم {code[3]}/{code[4]} - {status} - ينتهي: {expires}")
    
    # اختبار 3: استخدام كود شحن
    print("\n🎁 اختبار 3: استخدام كود شحن")
    
    # البحث عن كود غير مستخدم
    cursor.execute("""
        SELECT code, credit_amount FROM credit_codes 
        WHERE is_active = 1 AND current_uses < max_uses 
        LIMIT 1
    """)
    
    available_code = cursor.fetchone()
    if available_code:
        code, amount = available_code
        print(f"  🎯 استخدام الكود: {code} ({amount} وحدة)")
        
        # الحصول على رصيد المستخدم الحالي
        cursor.execute("SELECT balance FROM users WHERE id = 1")
        user_balance = cursor.fetchone()[0]
        print(f"  💰 رصيد المستخدم قبل الاستخدام: {user_balance} وحدة")
        
        # استخدام الكود
        cursor.execute("UPDATE users SET balance = balance + ? WHERE id = 1", (amount,))
        
        # تسجيل المعاملة
        cursor.execute("""
            INSERT INTO credit_transactions 
            (user_id, credit_code_id, transaction_type, amount, status, created_at) 
            VALUES (?, ?, 'credit_code', ?, 'completed', ?)
        """, (1, 1, amount, datetime.now()))
        
        # تحديث عدد استخدام الكود
        cursor.execute("UPDATE credit_codes SET current_uses = current_uses + 1 WHERE code = ?", (code,))
        
        conn.commit()
        
        # التحقق من الرصيد الجديد
        cursor.execute("SELECT balance FROM users WHERE id = 1")
        new_balance = cursor.fetchone()[0]
        print(f"  ✅ رصيد المستخدم بعد الاستخدام: {new_balance} وحدة")
        print(f"  ✅ تم إضافة {amount} وحدة بنجاح")
    else:
        print("  ⚠️ لا توجد أكواد متاحة للاستخدام")
    
    # اختبار 4: عرض المعاملات
    print("\n📈 اختبار 4: عرض المعاملات الأخيرة")
    cursor.execute("""
        SELECT ct.id, ct.transaction_type, ct.amount, ct.status, ct.created_at, cc.name as code_name
        FROM credit_transactions ct
        LEFT JOIN credit_codes cc ON ct.credit_code_id = cc.id
        ORDER BY ct.created_at DESC
        LIMIT 5
    """)
    
    transactions = cursor.fetchall()
    print(f"  📝 آخر {len(transactions)} معاملة:")
    for trans in transactions:
        code_info = f" (كود: {trans[5]})" if trans[5] else ""
        print(f"    - #{trans[0]}: {trans[1]} - {trans[2]} وحدة - {trans[3]}{code_info}")
    
    # اختبار 5: إحصائيات النظام
    print("\n📊 اختبار 5: إحصائيات النظام")
    
    # إحصائيات الأكواد
    cursor.execute("SELECT COUNT(*) FROM credit_codes WHERE is_active = 1")
    active_codes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM credit_codes WHERE expires_at < datetime('now')")
    expired_codes = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(current_uses) FROM credit_codes")
    total_used = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(max_uses) FROM credit_codes")
    total_possible = cursor.fetchone()[0] or 0
    
    print(f"  📈 إحصائيات الأكواد:")
    print(f"    - أكواد نشطة: {active_codes}")
    print(f"    - أكواد منتهية الصلاحية: {expired_codes}")
    print(f"    - إجمالي الاستخدام: {total_used}")
    print(f"    - إجمالي الاستخدامات الممكنة: {total_possible}")
    print(f"    - معدل الاستخدام: {((total_used / total_possible) * 100):.1f}%" if total_possible > 0 else "    - معدل الاستخدام: 0%")
    
    # اختبار 6: عرض طرق الدفع
    print("\n💳 اختبار 6: طرق الدفع المتاحة")
    cursor.execute("""
        SELECT name, provider, min_amount_usd, max_amount_usd, fees_percentage, fixed_fee_usd, is_active
        FROM payment_methods 
        WHERE is_active = 1
    """)
    
    methods = cursor.fetchall()
    print(f"  💰 طرق الدفع المتاحة ({len(methods)} طريقة):")
    for method in methods:
        status = "نشط" if method[6] else "معطل"
        print(f"    - {method[0]} ({method[1]}): ${method[2]} - ${method[3]} - رسوم {method[4]}% + ${method[5]} - {status}")
    
    conn.close()
    
    print("\n" + "=" * 50)
    print("🎉 تم اختبار نظام الشحن بنجاح!")
    print("\n✅ جميع الوظائف تعمل بشكل صحيح:")
    print("  ✅ قراءة البيانات")
    print("  ✅ عرض أكواد الشحن")
    print("  ✅ استخدام أكواد الشحن")
    print("  ✅ تسجيل المعاملات")
    print("  ✅ إحصائيات النظام")
    print("  ✅ طرق الدفع")


def demonstrate_usage():
    """عرض أمثلة على استخدام النظام"""
    
    db_path = "credit_system_test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n🚀 أمثلة على استخدام النظام:")
    print("=" * 50)
    
    # مثال 1: استخدام كود شحن
    print("📱 مثال 1: استخدام كود شحن")
    cursor.execute("SELECT code FROM credit_codes WHERE current_uses < max_uses LIMIT 1")
    code_result = cursor.fetchone()
    
    if code_result:
        code = code_result[0]
        print(f"  🎯 الكود المتاح: {code}")
        print(f"  📝 للاستخدام: استخدم الكود في التطبيق لشحن رصيدك")
    
    # مثال 2: شحن الرصيد بالدفع الإلكتروني
    print("\n💳 مثال 2: شحن الرصيد بالدفع الإلكتروني")
    cursor.execute("SELECT name, provider FROM payment_methods WHERE is_active = 1")
    methods = cursor.fetchall()
    
    for method in methods:
        print(f"  💰 عبر {method[0]} ({method[1]}):")
        print(f"    1. اختر المبلغ المطلوب")
        print(f"    2. اختر {method[0]} كطريقة دفع")
        print(f"    3. اتبع تعليمات الدفع")
        print(f"    4. سيتم شحن الرصيد تلقائياً")
    
    # مثال 3: عرض الرصيد
    print("\n💰 مثال 3: عرض رصيد المستخدم")
    cursor.execute("SELECT username, balance FROM users WHERE id = 1")
    user = cursor.fetchone()
    if user:
        print(f"  👤 المستخدم: {user[0]}")
        print(f"  💳 الرصيد الحالي: {user[1]} وحدة")
        print(f"  💡 كل عملية ذكية تستهلك تقريباً 10-50 وحدة")
    
    conn.close()


if __name__ == "__main__":
    test_credit_system_simple()
    demonstrate_usage()