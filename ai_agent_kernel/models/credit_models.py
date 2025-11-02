"""
نماذج نظام شحن الرصيد والدفع الإلكتروني
Credit System and Electronic Payment Models
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, DECIMAL, JSON, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base


class CreditCode(Base):
    """جدول أكواد الشحن"""
    __tablename__ = "credit_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    credit_amount = Column(Integer, nullable=False)  # Amount in units
    discount_percentage = Column(DECIMAL(5, 2), default=0.0)  # Discount if applicable
    max_uses = Column(Integer, default=1)  # Maximum number of uses
    current_uses = Column(Integer, default=0)  # Current usage count
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True))
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    transactions = relationship("CreditTransaction", back_populates="credit_code", cascade="all, delete-orphan")


class CreditTransaction(Base):
    """جدول معاملات شحن الرصيد"""
    __tablename__ = "credit_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    credit_code_id = Column(Integer, ForeignKey("credit_codes.id", ondelete="CASCADE"), nullable=True)
    transaction_type = Column(String(50), nullable=False)  # 'purchase', 'gift', 'refund', 'deduction'
    amount = Column(Integer, nullable=False)  # Amount in units
    amount_usd = Column(DECIMAL(10, 2), default=0.0)  # Amount in USD
    payment_method = Column(String(50))  # 'credit_code', 'stripe', 'plisio', 'admin'
    payment_id = Column(String(255))  # External payment ID
    status = Column(String(50), default="pending")  # 'pending', 'completed', 'failed', 'refunded'
    meta_data= Column(JSON, default={})  # Additional transaction data
    processed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    credit_code = relationship("CreditCode", back_populates="transactions")
    processor = relationship("User", foreign_keys=[processed_by])
    payment_records = relationship("PaymentRecord", back_populates="credit_transaction", cascade="all, delete-orphan")


class PaymentMethod(Base):
    """جدول طرق الدفع"""
    __tablename__ = "payment_methods"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    provider = Column(String(100), nullable=False)  # 'stripe', 'plisio'
    is_active = Column(Boolean, default=True, nullable=False)
    min_amount_usd = Column(DECIMAL(10, 2), default=1.0)
    max_amount_usd = Column(DECIMAL(10, 2), default=1000.0)
    supported_currencies = Column(JSON, default=["USD"])  # Supported currencies
    fees_percentage = Column(DECIMAL(5, 2), default=0.0)  # Provider fees
    fixed_fee_usd = Column(DECIMAL(10, 2), default=0.0)  # Fixed fee
    meta_data= Column(JSON, default={})  # Provider configuration
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    payment_records = relationship("PaymentRecord", back_populates="payment_method")


class PaymentRecord(Base):
    """جدول سجل الدفعات"""
    __tablename__ = "payment_records"
    
    id = Column(Integer, primary_key=True, index=True)
    credit_transaction_id = Column(Integer, ForeignKey("credit_transactions.id", ondelete="CASCADE"), nullable=False)
    payment_method_id = Column(Integer, ForeignKey("payment_methods.id", ondelete="CASCADE"), nullable=False)
    external_payment_id = Column(String(255), nullable=True)  # Payment provider ID
    payment_intent_id = Column(String(255))  # Stripe PaymentIntent ID
    session_id = Column(String(255))  # Plisio session ID
    amount_usd = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(String(50), default="pending")  # 'pending', 'processing', 'succeeded', 'failed', 'cancelled'
    gateway_response = Column(JSON, default={})  # Provider response data
    webhook_data = Column(JSON, default={})  # Webhook notification data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    credit_transaction = relationship("CreditTransaction", back_populates="payment_records")
    payment_method = relationship("PaymentMethod", back_populates="payment_records")


class Subscription(Base):
    """جدول الاشتراكات الشهرية"""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_name = Column(String(100), nullable=False)
    monthly_credits = Column(Integer, nullable=False)
    monthly_price_usd = Column(DECIMAL(10, 2), nullable=False)
    payment_method_id = Column(Integer, ForeignKey("payment_methods.id", ondelete="SET NULL"))
    status = Column(String(50), default="active")  # 'active', 'cancelled', 'expired'
    starts_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    next_billing_date = Column(DateTime(timezone=True))
    auto_renewal = Column(Boolean, default=True)
    meta_data= Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    payment_method = relationship("PaymentMethod")


# Import models to register them with Base
__all__ = [
    "CreditCode",
    "CreditTransaction", 
    "PaymentMethod",
    "PaymentRecord",
    "Subscription"
]