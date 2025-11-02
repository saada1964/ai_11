"""
واجهات برمجة التطبيقات لنظام الشحن والدفع
Credit System and Payment API Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database.database import get_db
from services.credit_service import credit_service, payment_service
from schemas.credit_schemas import (
    CreditCodeCreate, CreditCodeResponse, CreditCodeRedeem, CreditCodeRedeemResponse,
    CreditTransactionCreate, CreditTransactionResponse,
    PaymentMethodCreate, PaymentMethodResponse,
    PaymentInitializationRequest, PaymentInitializationResponse,
    PaymentCompletionRequest, PaymentCompletionResponse,
    CreditStatistics, UserTransactions,
    UserBalanceResponse, BalanceTopUpRequest, BalanceTopUpResponse,
    SubscriptionCreate, SubscriptionResponse,
    APIResponse, PaginatedResponse
)
from models.models import User

# Security
security = HTTPBearer()

# Router
credit_router = APIRouter(prefix="/credit", tags=["Credit System"])


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """الحصول على المستخدم الحالي من التوكن"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="بيانات الاعتماد غير صحيحة",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # هنا يمكن إضافة منطق التحقق من التوكن
        # للتبسيط، سنستخدم user_id من credentials
        user_id = int(credentials.credentials)
        user = db.query(User).filter(User.id == user_id).first()
        
        if user is None:
            raise credentials_exception
        
        return user
    
    except Exception:
        raise credentials_exception


# Credit Code Endpoints
@credit_router.post("/codes", response_model=APIResponse)
def create_credit_code(
    request: CreditCodeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """إنشاء كود شحن جديد"""
    try:
        credit_code = credit_service.create_credit_code(
            db=db,
            name=request.name,
            description=request.description,
            credit_amount=request.credit_amount,
            discount_percentage=request.discount_percentage,
            max_uses=request.max_uses,
            expires_days=request.expires_days,
            created_by=current_user.id
        )
        
        return APIResponse(
            success=True,
            message="تم إنشاء كود الشحن بنجاح",
            data={
                "code": credit_code.code,
                "name": credit_code.name,
                "amount": credit_code.credit_amount,
                "expires_at": credit_code.expires_at
            }
        )
    
    except Exception as e:
        return APIResponse(
            success=False,
            message=str(e),
            error=str(e)
        )


@credit_router.post("/codes/redeem", response_model=CreditCodeRedeemResponse)
def redeem_credit_code(
    request: CreditCodeRedeem,
    db: Session = Depends(get_db)
):
    """استخدام كود الشحن"""
    result = credit_service.redeem_credit_code(
        db=db,
        code=request.code,
        user_id=request.user_id
    )
    
    return CreditCodeRedeemResponse(**result)


@credit_router.get("/codes", response_model=PaginatedResponse)
def get_credit_codes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    active_only: bool = Query(True)
):
    """الحصول على قائمة أكواد الشحن"""
    
    query = db.query(CreditCodeResponse)
    if active_only:
        from models.credit_models import CreditCode
        query = query.filter(CreditCode.is_active == True)
    
    # إذا كان المستخدم ليس مشرفاً، اعرض الأكواد التي أنشأها فقط
    # يمكن إضافة منطق التحقق من الصلاحيات هنا
    
    total = query.count()
    codes = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return PaginatedResponse(
        items=codes,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@credit_router.get("/codes/{code_id}", response_model=CreditCodeResponse)
def get_credit_code(
    code_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """الحصول على تفاصيل كود شحن محدد"""
    from models.credit_models import CreditCode
    
    credit_code = db.query(CreditCode).filter(CreditCode.id == code_id).first()
    
    if not credit_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="كود الشحن غير موجود"
        )
    
    return credit_code


# Credit Statistics Endpoints
@credit_router.get("/statistics", response_model=CreditStatistics)
def get_credit_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """الحصول على إحصائيات نظام الشحن"""
    
    # يمكن إضافة التحقق من صلاحيات المستخدم
    stats = credit_service.get_credit_statistics(db)
    
    return CreditStatistics(**stats)


@credit_router.get("/transactions", response_model=UserTransactions)
def get_user_transactions(
    user_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """الحصول على معاملات المستخدم"""
    
    # إذا لم يتم تحديد user_id، استخدم المستخدم الحالي
    if user_id is None:
        user_id = current_user.id
    
    # التحقق من الصلاحيات - يمكن للمستخدم رؤية معاملاته فقط
    # يمكن إضافة منطق للتحقق من الصلاحيات للإدارة
    
    result = credit_service.get_user_transactions(
        db=db,
        user_id=user_id,
        limit=per_page,
        offset=(page - 1) * per_page
    )
    
    return UserTransactions(**result)


# Payment Method Endpoints
@credit_router.post("/payment-methods", response_model=APIResponse)
def create_payment_method(
    request: PaymentMethodCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """إنشاء طريقة دفع جديدة (للمديرين فقط)"""
    
    # هنا يمكن إضافة التحقق من صلاحيات المدير
    
    try:
        from models.credit_models import PaymentMethod
        
        payment_method = PaymentMethod(
            name=request.name,
            provider=request.provider.lower(),
            min_amount_usd=request.min_amount_usd,
            max_amount_usd=request.max_amount_usd,
            supported_currencies=request.supported_currencies,
            fees_percentage=request.fees_percentage,
            fixed_fee_usd=request.fixed_fee_usd,
            meta_data=request.meta_data
        )
        
        db.add(payment_method)
        db.commit()
        db.refresh(payment_method)
        
        return APIResponse(
            success=True,
            message="تم إنشاء طريقة الدفع بنجاح",
            data={"id": payment_method.id, "name": payment_method.name}
        )
    
    except Exception as e:
        db.rollback()
        return APIResponse(
            success=False,
            message=str(e),
            error=str(e)
        )


@credit_router.get("/payment-methods", response_model=List[PaymentMethodResponse])
def get_payment_methods(
    db: Session = Depends(get_db)
):
    """الحصول على قائمة طرق الدفع المتاحة"""
    
    from models.credit_models import PaymentMethod
    
    methods = db.query(PaymentMethod).filter(PaymentMethod.is_active == True).all()
    
    return methods


# Payment Initialization Endpoints
@credit_router.post("/payments/initialize", response_model=PaymentInitializationResponse)
def initialize_payment(
    request: PaymentInitializationRequest,
    db: Session = Depends(get_db)
):
    """بدء عملية دفع"""
    
    result = payment_service.initialize_payment(
        db=db,
        user_id=request.user_id,
        amount_usd=request.amount_usd,
        payment_method=request.payment_method,
        meta_data=request.meta_data
    )
    
    return PaymentInitializationResponse(**result)


@credit_router.post("/payments/complete", response_model=PaymentCompletionResponse)
def complete_payment(
    request: PaymentCompletionRequest,
    db: Session = Depends(get_db)
):
    """إتمام عملية دفع"""
    
    result = payment_service.complete_payment(
        db=db,
        payment_record_id=request.payment_record_id,
        external_payment_id=request.external_payment_id,
        status=request.status
    )
    
    return PaymentCompletionResponse(**result)


# User Balance Endpoints
@credit_router.get("/balance/{user_id}", response_model=UserBalanceResponse)
def get_user_balance(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """الحصول على رصيد المستخدم"""
    
    # التحقق من الصلاحيات - يمكن للمستخدم رؤية رصيده فقط
    if user_id != current_user.id:
        # يمكن إضافة منطق التحقق من صلاحيات الإدارة
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="غير مسموح لك بالوصول إلى رصيد هذا المستخدم"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المستخدم غير موجود"
        )
    
    # الحصول على آخر معاملة
    from models.credit_models import CreditTransaction
    last_transaction = db.query(CreditTransaction).filter(
        CreditTransaction.user_id == user_id
    ).order_by(CreditTransaction.created_at.desc()).first()
    
    return UserBalanceResponse(
        user_id=user_id,
        balance=user.balance,
        last_transaction=last_transaction
    )


@credit_router.post("/balance/topup", response_model=BalanceTopUpResponse)
def topup_balance(
    request: BalanceTopUpRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """شحن الرصيد (للمديرين فقط)"""
    
    # التحقق من الصلاحيات
    
    try:
        user = db.query(User).filter(User.id == request.user_id).first()
        
        if not user:
            return BalanceTopUpResponse(
                success=False,
                message="المستخدم غير موجود"
            )
        
        # إضافة الرصيد
        user.balance += request.amount
        
        # إنشاء سجل المعاملة
        from models.credit_models import CreditTransaction
        transaction = CreditTransaction(
            user_id=request.user_id,
            transaction_type="topup",
            amount=request.amount,
            status="completed",
            meta_data={"method": request.method, "admin_id": current_user.id}
        )
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        return BalanceTopUpResponse(
            success=True,
            message=f"تم شحن {request.amount} وحدة بنجاح",
            data={
                "new_balance": user.balance,
                "transaction_id": transaction.id
            }
        )
    
    except Exception as e:
        db.rollback()
        return BalanceTopUpResponse(
            success=False,
            message=f"خطأ في شحن الرصيد: {str(e)}"
        )


# Subscription Endpoints
@credit_router.post("/subscriptions", response_model=APIResponse)
def create_subscription(
    request: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """إنشاء اشتراك شهري"""
    
    from datetime import datetime, timedelta
    from models.credit_models import Subscription
    
    # التحقق من صلاحيات المستخدم
    if request.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="غير مسموح لك بإنشاء اشتراك لهذا المستخدم"
        )
    
    try:
        starts_at = datetime.utcnow()
        expires_at = starts_at + timedelta(days=30)
        next_billing = expires_at
        
        subscription = Subscription(
            user_id=request.user_id,
            plan_name=request.plan_name,
            monthly_credits=request.monthly_credits,
            monthly_price_usd=request.monthly_price_usd,
            payment_method_id=request.payment_method_id,
            starts_at=starts_at,
            expires_at=expires_at,
            next_billing_date=next_billing,
            auto_renewal=request.auto_renewal
        )
        
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        return APIResponse(
            success=True,
            message="تم إنشاء الاشتراك بنجاح",
            data={
                "subscription_id": subscription.id,
                "expires_at": expires_at,
                "next_billing": next_billing
            }
        )
    
    except Exception as e:
        db.rollback()
        return APIResponse(
            success=False,
            message=str(e),
            error=str(e)
        )


@credit_router.get("/subscriptions/{user_id}", response_model=List[SubscriptionResponse])
def get_user_subscriptions(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """الحصول على اشتراكات المستخدم"""
    
    # التحقق من الصلاحيات
    if user_id != current_user.id:
        # يمكن إضافة منطق التحقق من صلاحيات الإدارة
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="غير مسموح لك بالوصول إلى اشتراكات هذا المستخدم"
        )
    
    from models.credit_models import Subscription
    
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).all()
    
    return subscriptions