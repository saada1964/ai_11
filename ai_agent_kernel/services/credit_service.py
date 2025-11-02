"""
خدمة نظام شحن الرصيد والدفع الإلكتروني
Credit System and Electronic Payment Service
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from models.models import User
from models.credit_models import (
    CreditCode, CreditTransaction, PaymentMethod, 
    PaymentRecord, Subscription
)


class CreditService:
    """خدمة نظام الشحن"""
    
    @staticmethod
    def generate_credit_code(length: int = 8) -> str:
        """إنشاء كود شحن عشوائي"""
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def validate_credit_code(code: str) -> bool:
        """التحقق من صحة كود الشحن"""
        # التحقق من الطول والأحرف المسموحة
        if len(code) < 6 or len(code) > 20:
            return False
        
        # التحقق من أن الكود يحتوي على أحرف مسموحة فقط
        allowed_chars = string.ascii_uppercase + string.digits
        return all(c in allowed_chars for c in code)
    
    @classmethod
    def create_credit_code(
        cls,
        db: Session,
        name: str,
        description: str,
        credit_amount: int,
        discount_percentage: float = 0.0,
        max_uses: int = 1,
        expires_days: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> CreditCode:
        """إنشاء كود شحن جديد"""
        
        # التحقق من صحة البيانات
        if credit_amount <= 0:
            raise ValueError("مبلغ الشحن يجب أن يكون أكبر من صفر")
        
        if max_uses <= 0:
            raise ValueError("عدد الاستخدامات يجب أن يكون أكبر من صفر")
        
        if not cls.validate_credit_code(name):
            raise ValueError("اسم الكود غير صحيح")
        
        # إنشاء كود فريد
        code = cls.generate_credit_code()
        while db.query(CreditCode).filter(CreditCode.code == code).first():
            code = cls.generate_credit_code()
        
        # تحديد تاريخ انتهاء الصلاحية
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        # إنشاء الكود
        credit_code = CreditCode(
            code=code,
            name=name,
            description=description,
            credit_amount=credit_amount,
            discount_percentage=discount_percentage,
            max_uses=max_uses,
            expires_at=expires_at,
            created_by=created_by
        )
        
        db.add(credit_code)
        db.commit()
        db.refresh(credit_code)
        
        return credit_code
    
    @classmethod
    def redeem_credit_code(
        cls,
        db: Session,
        code: str,
        user_id: int
    ) -> Dict[str, Any]:
        """استخدام كود الشحن"""
        
        # البحث عن الكود
        credit_code = db.query(CreditCode).filter(
            and_(
                CreditCode.code == code.upper(),
                CreditCode.is_active == True
            )
        ).first()
        
        if not credit_code:
            return {
                "success": False,
                "message": "كود الشحن غير موجود أو غير صحيح"
            }
        
        # التحقق من تاريخ انتهاء الصلاحية
        if credit_code.expires_at and credit_code.expires_at < datetime.utcnow():
            return {
                "success": False,
                "message": "كود الشحن منتهي الصلاحية"
            }
        
        # التحقق من عدد الاستخدامات
        if credit_code.current_uses >= credit_code.max_uses:
            return {
                "success": False,
                "message": "تم استخدام الحد الأقصى لهذا الكود"
            }
        
        # البحث عن المستخدم
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "message": "المستخدم غير موجود"
            }
        
        # التحقق من عدم استخدام الكود من قبل (للأكواد المفردة الاستخدام)
        if credit_code.max_uses == 1:
            existing_transaction = db.query(CreditTransaction).filter(
                and_(
                    CreditTransaction.credit_code_id == credit_code.id,
                    CreditTransaction.user_id == user_id,
                    CreditTransaction.status == "completed"
                )
            ).first()
            
            if existing_transaction:
                return {
                    "success": False,
                    "message": "تم استخدام هذا الكود مسبقاً"
                }
        
        try:
            # إضافة الرصيد للمستخدم
            user.balance += credit_code.credit_amount
            
            # تحديث عدد استخدام الكود
            credit_code.current_uses += 1
            
            # إنشاء سجل المعاملة
            transaction = CreditTransaction(
                user_id=user_id,
                credit_code_id=credit_code.id,
                transaction_type="credit_code",
                amount=credit_code.credit_amount,
                status="completed",
                meta_data={
                    "code_name": credit_code.name,
                    "code_description": credit_code.description
                }
            )
            
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            
            return {
                "success": True,
                "message": f"تم شحن {credit_code.credit_amount} وحدة بنجاح",
                "data": {
                    "amount": credit_code.credit_amount,
                    "new_balance": user.balance,
                    "transaction_id": transaction.id
                }
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"خطأ في المعاملة: {str(e)}"
            }
    
    @classmethod
    def get_credit_statistics(
        cls,
        db: Session,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """إحصائيات نظام الشحن"""
        
        query = db.query(CreditCode)
        if user_id:
            query = query.filter(CreditCode.created_by == user_id)
        
        # إحصائيات الأكواد
        total_codes = query.count()
        active_codes = query.filter(CreditCode.is_active == True).count()
        expired_codes = query.filter(
            and_(
                CreditCode.expires_at < datetime.utcnow(),
                CreditCode.is_active == True
            )
        ).count()
        
        # إحصائيات الاستخدام
        total_redeemed = db.query(CreditTransaction).filter(
            CreditTransaction.credit_code_id.isnot(None)
        ).count()
        
        # أكثر الأكواد استخداماً
        top_codes = db.query(
            CreditCode.name,
            CreditCode.code,
            CreditCode.credit_amount,
            CreditCode.current_uses
        ).order_by(desc(CreditCode.current_uses)).limit(5).all()
        
        return {
            "codes": {
                "total": total_codes,
                "active": active_codes,
                "expired": expired_codes
            },
            "usage": {
                "total_redeemed": total_redeemed
            },
            "top_codes": [
                {
                    "name": code.name,
                    "code": code.code,
                    "amount": code.credit_amount,
                    "uses": code.current_uses
                }
                for code in top_codes
            ]
        }
    
    @classmethod
    def get_user_transactions(
        cls,
        db: Session,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """معاملات المستخدم"""
        
        transactions = db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id
        ).order_by(desc(CreditTransaction.created_at)).limit(limit).offset(offset).all()
        
        # إجمالي المعاملات
        total = db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id
        ).count()
        
        return {
            "transactions": [
                {
                    "id": t.id,
                    "type": t.transaction_type,
                    "amount": t.amount,
                    "amount_usd": float(t.amount_usd) if t.amount_usd else 0.0,
                    "status": t.status,
                    "payment_method": t.payment_method,
                    "created_at": t.created_at.isoformat(),
                    "code_name": t.credit_code.name if t.credit_code else None
                }
                for t in transactions
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }


class PaymentService:
    """خدمة الدفع الإلكتروني"""
    
    @classmethod
    def initialize_payment(
        cls,
        db: Session,
        user_id: int,
        amount_usd: float,
        payment_method: str,
        meta_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """بدء عملية دفع"""
        
        # البحث عن طريقة الدفع
        method = db.query(PaymentMethod).filter(
            and_(
                PaymentMethod.provider == payment_method.lower(),
                PaymentMethod.is_active == True
            )
        ).first()
        
        if not method:
            return {
                "success": False,
                "message": f"طريقة الدفع {payment_method} غير مدعومة"
            }
        
        # التحقق من الحد الأدنى والأقصى
        amount_decimal = Decimal(str(amount_usd))
        if amount_decimal < method.min_amount_usd:
            return {
                "success": False,
                "message": f"الحد الأدنى للدفع هو ${float(method.min_amount_usd)}"
            }
        
        if amount_decimal > method.max_amount_usd:
            return {
                "success": False,
                "message": f"الحد الأقصى للدفع هو ${float(method.max_amount_usd)}"
            }
        
        # حساب الرسوم
        fees_percentage = (amount_decimal * method.fees_percentage / 100)
        total_with_fees = amount_decimal + fees_percentage + method.fixed_fee_usd
        
        # تحويل المبلغ إلى وحدات (افتراض 1 دولار = 100 وحدة)
        credit_units = int(amount_decimal * 100)
        
        try:
            # إنشاء سجل المعاملة
            transaction = CreditTransaction(
                user_id=user_id,
                transaction_type="purchase",
                amount=credit_units,
                amount_usd=amount_usd,
                payment_method=payment_method,
                status="pending",
                meta_data=meta_data or {}
            )
            
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            
            # إنشاء سجل الدفع
            payment_record = PaymentRecord(
                credit_transaction_id=transaction.id,
                payment_method_id=method.id,
                amount_usd=amount_usd,
                status="pending"
            )
            
            db.add(payment_record)
            db.commit()
            db.refresh(payment_record)
            
            return {
                "success": True,
                "message": "تم بدء عملية الدفع",
                "data": {
                    "transaction_id": transaction.id,
                    "payment_record_id": payment_record.id,
                    "amount_usd": float(amount_usd),
                    "credit_units": credit_units,
                    "fees": float(total_with_fees - amount_decimal),
                    "total_amount": float(total_with_fees)
                }
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"خطأ في إنشاء الدفع: {str(e)}"
            }
    
    @classmethod
    def complete_payment(
        cls,
        db: Session,
        payment_record_id: int,
        external_payment_id: Optional[str] = None,
        status: str = "succeeded"
    ) -> Dict[str, Any]:
        """إتمام عملية الدفع"""
        
        # البحث عن سجل الدفع
        payment_record = db.query(PaymentRecord).filter(
            PaymentRecord.id == payment_record_id
        ).first()
        
        if not payment_record:
            return {
                "success": False,
                "message": "سجل الدفع غير موجود"
            }
        
        # تحديث حالة الدفع
        payment_record.status = status
        payment_record.external_payment_id = external_payment_id
        payment_record.completed_at = datetime.utcnow()
        
        # تحديث حالة المعاملة
        transaction = payment_record.credit_transaction
        if status == "succeeded":
            # إضافة الرصيد للمستخدم
            user = db.query(User).filter(User.id == transaction.user_id).first()
            user.balance += transaction.amount
            
            transaction.status = "completed"
        else:
            transaction.status = "failed"
        
        try:
            db.commit()
            return {
                "success": True,
                "message": "تم تحديث حالة الدفع",
                "data": {
                    "payment_status": status,
                    "transaction_status": transaction.status,
                    "new_balance": user.balance if status == "succeeded" else None
                }
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"خطأ في تحديث الدفع: {str(e)}"
            }


# إنشاء singleton instances
credit_service = CreditService()
payment_service = PaymentService()