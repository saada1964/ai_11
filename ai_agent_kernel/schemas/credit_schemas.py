"""
مخططات البيانات لنظام الشحن والدفع
Credit System and Payment Data Schemas
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from decimal import Decimal


# Credit Code Schemas
class CreditCodeBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, description="اسم كود الشحن")
    description: Optional[str] = Field(None, description="وصف الكود")
    credit_amount: int = Field(..., gt=0, description="مبلغ الشحن بالوحدات")
    discount_percentage: Optional[float] = Field(0.0, ge=0, le=100, description="نسبة الخصم")
    max_uses: int = Field(1, gt=0, description="الحد الأقصى للاستخدام")
    expires_days: Optional[int] = Field(None, gt=0, description="عدد أيام انتهاء الصلاحية")


class CreditCodeCreate(CreditCodeBase):
    """إنشاء كود شحن جديد"""
    created_by: Optional[int] = Field(None, description="المستخدم الذي أنشأ الكود")


class CreditCodeResponse(BaseModel):
    """استجابة كود الشحن"""
    id: int
    code: str
    name: str
    description: Optional[str]
    credit_amount: int
    discount_percentage: float
    max_uses: int
    current_uses: int
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CreditCodeRedeem(BaseModel):
    """استخدام كود الشحن"""
    code: str = Field(..., min_length=6, max_length=20, description="كود الشحن")
    user_id: int = Field(..., description="معرف المستخدم")


class CreditCodeRedeemResponse(BaseModel):
    """استجابة استخدام كود الشحن"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# Credit Transaction Schemas
class CreditTransactionBase(BaseModel):
    transaction_type: str = Field(..., description="نوع المعاملة")
    amount: int = Field(..., description="المبلغ بالوحدات")
    amount_usd: Optional[float] = Field(0.0, description="المبلغ بالدولار الأمريكي")
    payment_method: Optional[str] = Field(None, description="طريقة الدفع")


class CreditTransactionCreate(CreditTransactionBase):
    """إنشاء معاملة شحن جديدة"""
    user_id: int = Field(..., description="معرف المستخدم")
    credit_code_id: Optional[int] = Field(None, description="معرف كود الشحن")
    meta_data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CreditTransactionResponse(BaseModel):
    """استجابة معاملة الشحن"""
    id: int
    user_id: int
    credit_code_id: Optional[int]
    transaction_type: str
    amount: int
    amount_usd: float
    payment_method: Optional[str]
    payment_id: Optional[str]
    status: str
    meta_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    # Optional relationships
    code_name: Optional[str] = None
    
    class Config:
        from_attributes = True


# Payment Method Schemas
class PaymentMethodBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="اسم طريقة الدفع")
    provider: str = Field(..., description="مقدم الخدمة")
    min_amount_usd: float = Field(1.0, ge=0, description="الحد الأدنى بالدولار")
    max_amount_usd: float = Field(1000.0, ge=0, description="الحد الأقصى بالدولار")
    supported_currencies: List[str] = Field(["USD"], description="العملات المدعومة")
    fees_percentage: float = Field(0.0, ge=0, le=100, description="نسبة الرسوم")
    fixed_fee_usd: float = Field(0.0, ge=0, description="رسوم ثابتة بالدولار")


class PaymentMethodCreate(PaymentMethodBase):
    """إنشاء طريقة دفع جديدة"""
    meta_data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PaymentMethodResponse(BaseModel):
    """استجابة طريقة الدفع"""
    id: int
    name: str
    provider: str
    is_active: bool
    min_amount_usd: float
    max_amount_usd: float
    supported_currencies: List[str]
    fees_percentage: float
    fixed_fee_usd: float
    meta_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Payment Record Schemas
class PaymentRecordBase(BaseModel):
    amount_usd: float = Field(..., gt=0, description="المبلغ بالدولار الأمريكي")
    currency: str = Field("USD", description="رمز العملة")
    status: str = Field("pending", description="حالة الدفع")


class PaymentRecordCreate(PaymentRecordBase):
    """إنشاء سجل دفع جديد"""
    credit_transaction_id: int = Field(..., description="معرف معاملة الشحن")
    payment_method_id: int = Field(..., description="معرف طريقة الدفع")


class PaymentRecordResponse(BaseModel):
    """استجابة سجل الدفع"""
    id: int
    credit_transaction_id: int
    payment_method_id: int
    external_payment_id: Optional[str]
    payment_intent_id: Optional[str]
    session_id: Optional[str]
    amount_usd: float
    currency: str
    status: str
    gateway_response: Dict[str, Any]
    webhook_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Payment Initialization Schemas
class PaymentInitializationRequest(BaseModel):
    """طلب بدء عملية دفع"""
    user_id: int = Field(..., description="معرف المستخدم")
    amount_usd: float = Field(..., gt=0, description="المبلغ بالدولار الأمريكي")
    payment_method: str = Field(..., description="طريقة الدفع")
    meta_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('payment_method')
    def validate_payment_method(cls, v):
        valid_methods = ['stripe', 'plisio', 'paypal', 'credit_card']
        if v.lower() not in valid_methods:
            raise ValueError(f'طريقة الدفع يجب أن تكون واحدة من: {valid_methods}')
        return v.lower()


class PaymentInitializationResponse(BaseModel):
    """استجابة بدء عملية الدفع"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# Payment Completion Schemas
class PaymentCompletionRequest(BaseModel):
    """طلب إتمام عملية دفع"""
    payment_record_id: int = Field(..., description="معرف سجل الدفع")
    external_payment_id: Optional[str] = Field(None, description="معرف الدفع الخارجي")
    status: str = Field("succeeded", description="حالة الدفع")
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['succeeded', 'failed', 'cancelled', 'pending']
        if v not in valid_statuses:
            raise ValueError(f'حالة الدفع يجب أن تكون واحدة من: {valid_statuses}')
        return v


class PaymentCompletionResponse(BaseModel):
    """استجابة إتمام عملية الدفع"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# Statistics Schemas
class CreditStatistics(BaseModel):
    """إحصائيات نظام الشحن"""
    codes: Dict[str, int]
    usage: Dict[str, int]
    top_codes: List[Dict[str, Any]]


class UserTransactions(BaseModel):
    """معاملات المستخدم"""
    transactions: List[CreditTransactionResponse]
    total: int
    limit: int
    offset: int


# User Balance Schemas
class UserBalanceResponse(BaseModel):
    """استجابة رصيد المستخدم"""
    user_id: int
    balance: int
    last_transaction: Optional[CreditTransactionResponse] = None


class BalanceTopUpRequest(BaseModel):
    """طلب شحن الرصيد"""
    user_id: int = Field(..., description="معرف المستخدم")
    amount: int = Field(..., gt=0, description="المبلغ بالوحدات")
    method: str = Field(..., description="طريقة الشحن")


class BalanceTopUpResponse(BaseModel):
    """استجابة شحن الرصيد"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# Subscription Schemas
class SubscriptionBase(BaseModel):
    plan_name: str = Field(..., description="اسم الخطة")
    monthly_credits: int = Field(..., gt=0, description="الرصيد الشهري")
    monthly_price_usd: float = Field(..., gt=0, description="السعر الشهري بالدولار")


class SubscriptionCreate(SubscriptionBase):
    """إنشاء اشتراك جديد"""
    user_id: int = Field(..., description="معرف المستخدم")
    payment_method_id: Optional[int] = Field(None, description="معرف طريقة الدفع")
    auto_renewal: bool = Field(True, description="التجديد التلقائي")


class SubscriptionResponse(BaseModel):
    """استجابة الاشتراك"""
    id: int
    user_id: int
    plan_name: str
    monthly_credits: int
    monthly_price_usd: float
    payment_method_id: Optional[int]
    status: str
    starts_at: datetime
    expires_at: datetime
    next_billing_date: Optional[datetime]
    auto_renewal: bool
    meta_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# API Response Wrapper
class APIResponse(BaseModel):
    """رد API عام"""
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None


class PaginatedResponse(BaseModel):
    """استجابة مجمعة بصفحات"""
    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int