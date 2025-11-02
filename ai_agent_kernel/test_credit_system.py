"""
اختبارات نظام الشحن والدفع
Credit System and Payment Tests
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database.database import get_db, engine
from models.models import User
from models.credit_models import CreditCode, CreditTransaction, PaymentMethod
from services.credit_service import CreditService, PaymentService
from schemas.credit_schemas import (
    CreditCodeCreate, PaymentInitializationRequest
)


class TestCreditService:
    """اختبارات خدمة الشحن"""
    
    @pytest.fixture
    def db_session(self):
        """إنشاء جلسة قاعدة بيانات للاختبار"""
        from sqlalchemy.orm import sessionmaker
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = TestingSessionLocal()
        yield db
        db.close()
    
    @pytest.fixture
    def test_user(self, db_session):
        """مستخدم اختبار"""
        user = User(
            username="test_user",
            email="test@example.com",
            hashed_password="hashed_password",
            balance=1000
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    @pytest.fixture
    def test_credit_code(self, db_session, test_user):
        """كود شحن اختبار"""
        credit_code = CreditCode(
            code="TEST123",
            name="كود اختبار",
            description="كود شحن للاختبار",
            credit_amount=500,
            max_uses=5,
            created_by=test_user.id
        )
        db_session.add(credit_code)
        db_session.commit()
        db_session.refresh(credit_code)
        return credit_code
    
    def test_generate_credit_code(self):
        """اختبار إنشاء كود عشوائي"""
        code = CreditService.generate_credit_code(8)
        
        assert len(code) == 8
        assert code.isupper()
        assert all(c.isalnum() for c in code)
    
    def test_validate_credit_code(self):
        """اختبار التحقق من صحة كود الشحن"""
        # أكواد صحيحة
        assert CreditService.validate_credit_code("TEST123")
        assert CreditService.validate_credit_code("ABCDEFGH")
        assert CreditService.validate_credit_code("12345678")
        
        # أكواد غير صحيحة
        assert not CreditService.validate_credit_code("TEST")  # قصير جداً
        assert not CreditService.validate_credit_code("TEST@123")  # يحتوي على رموز خاصة
        assert not CreditService.validate_credit_code("")  # فارغ
    
    def test_create_credit_code(self, db_session, test_user):
        """اختبار إنشاء كود شحن جديد"""
        result = CreditService.create_credit_code(
            db=db_session,
            name="كود جديد",
            description="وصف الكود",
            credit_amount=1000,
            max_uses=10,
            expires_days=30,
            created_by=test_user.id
        )
        
        assert result is not None
        assert result.name == "كود جديد"
        assert result.credit_amount == 1000
        assert result.max_uses == 10
        assert result.expires_at is not None
        assert result.created_by == test_user.id
    
    def test_create_credit_code_invalid_data(self, db_session, test_user):
        """اختبار إنشاء كود شحن ببيانات خاطئة"""
        # مبلغ شحن سالب
        with pytest.raises(ValueError, match="مبلغ الشحن يجب أن يكون أكبر من صفر"):
            CreditService.create_credit_code(
                db=db_session,
                name="كود خاطئ",
                description="وصف",
                credit_amount=-100,
                created_by=test_user.id
            )
        
        # عدد استخدامات سالب
        with pytest.raises(ValueError, match="عدد الاستخدامات يجب أن يكون أكبر من صفر"):
            CreditService.create_credit_code(
                db=db_session,
                name="كود خاطئ",
                description="وصف",
                credit_amount=100,
                max_uses=-1,
                created_by=test_user.id
            )
    
    def test_redeem_credit_code_success(self, db_session, test_user, test_credit_code):
        """اختبار استخدام كود شحن بنجاح"""
        initial_balance = test_user.balance
        
        result = CreditService.redeem_credit_code(
            db=db_session,
            code=test_credit_code.code,
            user_id=test_user.id
        )
        
        assert result["success"] is True
        assert "تم شحن" in result["message"]
        assert test_user.balance == initial_balance + test_credit_code.credit_amount
        
        # التحقق من تحديث عدد الاستخدامات
        db_session.refresh(test_credit_code)
        assert test_credit_code.current_uses == 1
    
    def test_redeem_nonexistent_code(self, db_session, test_user):
        """اختبار استخدام كود غير موجود"""
        result = CreditService.redeem_credit_code(
            db=db_session,
            code="NONEXISTENT",
            user_id=test_user.id
        )
        
        assert result["success"] is False
        assert "غير موجود" in result["message"]
    
    def test_redeem_expired_code(self, db_session, test_user):
        """اختبار استخدام كود منتهي الصلاحية"""
        expired_code = CreditCode(
            code="EXPIRED",
            name="كود منتهي",
            description="كود منتهي الصلاحية",
            credit_amount=500,
            expires_at=datetime.utcnow() - timedelta(days=1),
            created_by=test_user.id
        )
        db_session.add(expired_code)
        db_session.commit()
        
        result = CreditService.redeem_credit_code(
            db=db_session,
            code=expired_code.code,
            user_id=test_user.id
        )
        
        assert result["success"] is False
        assert "منتهي الصلاحية" in result["message"]
    
    def test_redeem_max_used_code(self, db_session, test_user, test_credit_code):
        """اختبار استخدام كود تم استخدام الحد الأقصى له"""
        # زيادة عدد الاستخدامات إلى الحد الأقصى
        test_credit_code.current_uses = test_credit_code.max_uses
        db_session.commit()
        
        result = CreditService.redeem_credit_code(
            db=db_session,
            code=test_credit_code.code,
            user_id=test_user.id
        )
        
        assert result["success"] is False
        assert "الحد الأقصى" in result["message"]
    
    def test_get_credit_statistics(self, db_session, test_user):
        """اختبار الحصول على إحصائيات نظام الشحن"""
        # إنشاء بعض الأكواد
        code1 = CreditService.create_credit_code(
            db=db_session,
            name="كود 1",
            description="أول كود",
            credit_amount=100,
            created_by=test_user.id
        )
        
        code2 = CreditService.create_credit_code(
            db=db_session,
            name="كود 2",
            description="ثاني كود",
            credit_amount=200,
            created_by=test_user.id
        )
        
        # استخدام كود
        test_user2 = User(
            username="user2",
            email="user2@example.com",
            hashed_password="password",
            balance=500
        )
        db_session.add(test_user2)
        db_session.commit()
        
        CreditService.redeem_credit_code(
            db=db_session,
            code=code1.code,
            user_id=test_user2.id
        )
        
        stats = CreditService.get_credit_statistics(db_session, test_user.id)
        
        assert "codes" in stats
        assert "usage" in stats
        assert "top_codes" in stats
        assert stats["codes"]["total"] == 2
        assert stats["usage"]["total_redeemed"] == 1
    
    def test_get_user_transactions(self, db_session, test_user, test_credit_code):
        """اختبار الحصول على معاملات المستخدم"""
        # استخدام كود الشحن
        CreditService.redeem_credit_code(
            db=db_session,
            code=test_credit_code.code,
            user_id=test_user.id
        )
        
        transactions = CreditService.get_user_transactions(db_session, test_user.id)
        
        assert "transactions" in transactions
        assert "total" in transactions
        assert transactions["total"] >= 1
        
        # التحقق من تفاصيل المعاملة
        if transactions["transactions"]:
            transaction = transactions["transactions"][0]
            assert transaction["type"] == "credit_code"
            assert transaction["amount"] == test_credit_code.credit_amount


class TestPaymentService:
    """اختبارات خدمة الدفع"""
    
    @pytest.fixture
    def db_session(self):
        """إنشاء جلسة قاعدة بيانات للاختبار"""
        from sqlalchemy.orm import sessionmaker
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = TestingSessionLocal()
        yield db
        db.close()
    
    @pytest.fixture
    def test_user(self, db_session):
        """مستخدم اختبار"""
        user = User(
            username="payment_user",
            email="payment@example.com",
            hashed_password="hashed_password",
            balance=1000
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    @pytest.fixture
    def payment_method(self, db_session):
        """طريقة دفع اختبار"""
        method = PaymentMethod(
            name="Test Payment",
            provider="test",
            min_amount_usd=1.0,
            max_amount_usd=1000.0,
            fees_percentage=2.9,
            fixed_fee_usd=0.30
        )
        db_session.add(method)
        db_session.commit()
        db_session.refresh(method)
        return method
    
    def test_initialize_payment_success(self, db_session, test_user, payment_method):
        """اختبار بدء عملية دفع بنجاح"""
        result = PaymentService.initialize_payment(
            db=db_session,
            user_id=test_user.id,
            amount_usd=50.0,
            payment_method="test"
        )
        
        assert result["success"] is True
        assert "تم بدء عملية الدفع" in result["message"]
        assert "transaction_id" in result["data"]
        assert "payment_record_id" in result["data"]
        assert result["data"]["amount_usd"] == 50.0
    
    def test_initialize_payment_invalid_method(self, db_session, test_user):
        """اختبار بدء عملية دفع بطريقة غير مدعومة"""
        result = PaymentService.initialize_payment(
            db=db_session,
            user_id=test_user.id,
            amount_usd=50.0,
            payment_method="invalid_method"
        )
        
        assert result["success"] is False
        assert "غير مدعومة" in result["message"]
    
    def test_initialize_payment_below_minimum(self, db_session, test_user, payment_method):
        """اختبار بدء عملية دفع ب amount أقل من الحد الأدنى"""
        result = PaymentService.initialize_payment(
            db=db_session,
            user_id=test_user.id,
            amount_usd=0.5,  # أقل من الحد الأدنى 1.0
            payment_method="test"
        )
        
        assert result["success"] is False
        assert "الحد الأدنى" in result["message"]
    
    def test_initialize_payment_above_maximum(self, db_session, test_user, payment_method):
        """اختبار بدء عملية دفع ب amount أكبر من الحد الأقصى"""
        result = PaymentService.initialize_payment(
            db=db_session,
            user_id=test_user.id,
            amount_usd=2000.0,  # أكبر من الحد الأقصى 1000.0
            payment_method="test"
        )
        
        assert result["success"] is False
        assert "الحد الأقصى" in result["message"]
    
    def test_complete_payment_success(self, db_session, test_user, payment_method):
        """اختبار إتمام عملية دفع بنجاح"""
        # بدء عملية دفع
        init_result = PaymentService.initialize_payment(
            db=db_session,
            user_id=test_user.id,
            amount_usd=50.0,
            payment_method="test"
        )
        
        payment_record_id = init_result["data"]["payment_record_id"]
        
        # إتمام عملية الدفع
        result = PaymentService.complete_payment(
            db=db_session,
            payment_record_id=payment_record_id,
            external_payment_id="ext_123",
            status="succeeded"
        )
        
        assert result["success"] is True
        assert "تم تحديث حالة الدفع" in result["message"]
        
        # التحقق من إضافة الرصيد
        db_session.refresh(test_user)
        assert test_user.balance > 1000  # رصيد المستخدم الأصلي
    
    def test_complete_payment_failed(self, db_session, test_user, payment_method):
        """اختبار إتمام عملية دفع فاشلة"""
        # بدء عملية دفع
        init_result = PaymentService.initialize_payment(
            db=db_session,
            user_id=test_user.id,
            amount_usd=50.0,
            payment_method="test"
        )
        
        payment_record_id = init_result["data"]["payment_record_id"]
        
        # إتمام عملية الدفع بفشل
        result = PaymentService.complete_payment(
            db=db_session,
            payment_record_id=payment_record_id,
            external_payment_id="ext_123",
            status="failed"
        )
        
        assert result["success"] is True  # العملية تمت بنجاح حتى لو فشل الدفع
        assert "transaction_status" in result["data"]
        assert result["data"]["transaction_status"] == "failed"


class TestCreditSchemas:
    """اختبارات مخططات البيانات"""
    
    def test_credit_code_create_valid(self):
        """اختبار إنشاء مخطط كود الشحن ببيانات صحيحة"""
        data = {
            "name": "كود اختبار",
            "description": "وصف الكود",
            "credit_amount": 1000,
            "discount_percentage": 10.0,
            "max_uses": 5,
            "expires_days": 30
        }
        
        schema = CreditCodeCreate(**data)
        assert schema.name == data["name"]
        assert schema.credit_amount == data["credit_amount"]
        assert schema.max_uses == data["max_uses"]
    
    def test_credit_code_create_invalid(self):
        """اختبار إنشاء مخطط كود الشحن ببيانات خاطئة"""
        # مبلغ شحن سالب
        with pytest.raises(ValueError):
            CreditCodeCreate(
                name="كود خاطئ",
                credit_amount=-100
            )
        
        # عدد استخدامات سالب
        with pytest.raises(ValueError):
            CreditCodeCreate(
                name="كود خاطئ",
                credit_amount=100,
                max_uses=-1
            )
    
    def test_payment_initialization_request_valid(self):
        """اختبار إنشاء مخطط طلب بدء الدفع ببيانات صحيحة"""
        data = {
            "user_id": 1,
            "amount_usd": 50.0,
            "payment_method": "stripe"
        }
        
        schema = PaymentInitializationRequest(**data)
        assert schema.user_id == data["user_id"]
        assert schema.amount_usd == data["amount_usd"]
        assert schema.payment_method == "stripe"
    
    def test_payment_initialization_request_invalid_method(self):
        """اختبار إنشاء مخطط طلب بدء الدفع بطريقة غير صحيحة"""
        with pytest.raises(ValueError):
            PaymentInitializationRequest(
                user_id=1,
                amount_usd=50.0,
                payment_method="invalid_method"
            )


# Integration Tests
class TestCreditSystemIntegration:
    """اختبارات تكامل نظام الشحن"""
    
    @pytest.fixture
    def db_session(self):
        """إنشاء جلسة قاعدة بيانات للاختبار"""
        from sqlalchemy.orm import sessionmaker
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = TestingSessionLocal()
        yield db
        db.close()
    
    @pytest.fixture
    def complete_setup(self, db_session):
        """إعداد كامل للاختبار"""
        # إنشاء مستخدم
        user = User(
            username="integration_user",
            email="integration@example.com",
            hashed_password="password",
            balance=1000
        )
        db_session.add(user)
        db_session.commit()
        
        # إنشاء كود شحن
        credit_code = CreditCode(
            code="INTEGRATE123",
            name="كود التكامل",
            description="كود اختبار التكامل",
            credit_amount=500,
            max_uses=10,
            created_by=user.id
        )
        db_session.add(credit_code)
        db_session.commit()
        
        # إنشاء طريقة دفع
        payment_method = PaymentMethod(
            name="Integration Test",
            provider="integration",
            min_amount_usd=1.0,
            max_amount_usd=1000.0
        )
        db_session.add(payment_method)
        db_session.commit()
        
        return {
            "user": user,
            "credit_code": credit_code,
            "payment_method": payment_method
        }
    
    def test_full_credit_flow(self, db_session, complete_setup):
        """اختبار تدفق كامل لشحن الرصيد"""
        user = complete_setup["user"]
        credit_code = complete_setup["credit_code"]
        
        initial_balance = user.balance
        
        # استخدام كود الشحن
        result = CreditService.redeem_credit_code(
            db=db_session,
            code=credit_code.code,
            user_id=user.id
        )
        
        assert result["success"] is True
        assert user.balance == initial_balance + credit_code.credit_amount
        
        # التحقق من إنشاء سجل المعاملة
        transactions = CreditService.get_user_transactions(db_session, user.id)
        assert transactions["total"] >= 1
        
        # التحقق من إحصائيات النظام
        stats = CreditService.get_credit_statistics(db_session)
        assert stats["usage"]["total_redeemed"] >= 1
    
    def test_full_payment_flow(self, db_session, complete_setup):
        """اختبار تدفق كامل لعملية الدفع"""
        user = complete_setup["user"]
        payment_method = complete_setup["payment_method"]
        
        initial_balance = user.balance
        amount_usd = 75.0
        
        # بدء عملية الدفع
        init_result = PaymentService.initialize_payment(
            db=db_session,
            user_id=user.id,
            amount_usd=amount_usd,
            payment_method="integration"
        )
        
        assert init_result["success"] is True
        
        payment_record_id = init_result["data"]["payment_record_id"]
        
        # إتمام عملية الدفع
        complete_result = PaymentService.complete_payment(
            db=db_session,
            payment_record_id=payment_record_id,
            external_payment_id="integration_ext_123",
            status="succeeded"
        )
        
        assert complete_result["success"] is True
        
        # التحقق من إضافة الرصيد (75 دولار = 7500 وحدة تقريباً)
        expected_units = int(amount_usd * 100)  # افتراض 1 دولار = 100 وحدة
        assert user.balance >= initial_balance + expected_units
        
        # التحقق من إنشاء سجل المعاملة
        transactions = CreditService.get_user_transactions(db_session, user.id)
        purchase_transactions = [
            t for t in transactions["transactions"] 
            if t["type"] == "purchase"
        ]
        assert len(purchase_transactions) >= 1


if __name__ == "__main__":
    # تشغيل الاختبارات
    pytest.main([__file__, "-v", "--tb=short"])