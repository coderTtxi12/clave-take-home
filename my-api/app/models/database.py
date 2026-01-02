"""
SQLAlchemy models for Restaurant Analytics Database
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
import enum

from sqlalchemy import (
    Column, Integer, String, Boolean, Numeric, Date, DateTime, Text,
    ForeignKey, Enum as SQLEnum, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


# ============================================================================
# ENUMS
# ============================================================================

class OrderSourceEnum(str, enum.Enum):
    """Order source systems"""
    TOAST = "toast"
    DOORDASH = "doordash"
    SQUARE = "square"


class OrderTypeEnum(str, enum.Enum):
    """Order types (normalized from all sources)"""
    DINE_IN = "dine_in"
    TAKEOUT = "takeout"
    DELIVERY = "delivery"
    PICKUP = "pickup"


class OrderStatusEnum(str, enum.Enum):
    """Order status"""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentTypeEnum(str, enum.Enum):
    """Payment types (normalized)"""
    CARD = "card"
    CASH = "cash"
    DIGITAL_WALLET = "digital_wallet"
    OTHER = "other"
    UNKNOWN = "unknown"


class PaymentStatusEnum(str, enum.Enum):
    """Payment status"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# ============================================================================
# MODELS
# ============================================================================

class Location(Base):
    """Master location/store data unified across all sources"""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    
    # Address components
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    country = Column(String(2), default="US")
    
    # Timezone for timestamp conversion
    timezone = Column(String(50), default="America/New_York")
    
    # Source-specific identifiers stored as JSONB
    source_ids = Column(JSONB)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    orders = relationship("Order", back_populates="location")


class Category(Base):
    """Product categories (normalized, no emojis)"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    
    # Normalized name without emojis/special chars
    normalized_name = Column(String(255), nullable=False)
    
    # Parent category for hierarchical structure
    parent_id = Column(Integer, ForeignKey("categories.id"))
    
    # Display order
    sort_order = Column(Integer, default=0)
    
    # Source mappings
    source_names = Column(JSONB)
    
    # Metadata
    description = Column(Text)
    extra_data = Column(JSONB)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    products = relationship("Product", back_populates="category")
    parent = relationship("Category", remote_side=[id])


class Product(Base):
    """Master product catalog (canonical names)"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    
    # Normalized name for matching
    normalized_name = Column(String(255), nullable=False)
    
    # Category
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    # Base price (can vary by location/source)
    base_price = Column(Numeric(10, 2))
    
    # Product details
    description = Column(Text)
    
    # Size/variation info
    size = Column(String(50))
    quantity = Column(String(50))
    
    # Is this product active?
    is_active = Column(Boolean, default=True)
    
    # Metadata
    extra_data = Column(JSONB)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    category = relationship("Category", back_populates="products")
    product_mappings = relationship("ProductMapping", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")


class ProductMapping(Base):
    """Maps source-specific product IDs to master products"""
    __tablename__ = "product_mappings"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    
    # Source system
    source = Column(SQLEnum(OrderSourceEnum), nullable=False)
    
    # Source-specific product identifier
    source_product_id = Column(String(255), nullable=False)
    
    # Original product name from source
    source_product_name = Column(String(255), nullable=False)
    
    # Price at source
    source_price = Column(Numeric(10, 2))
    
    # Match confidence
    match_confidence = Column(Numeric(3, 2))
    
    # Was this manually verified?
    is_manual_match = Column(Boolean, default=False)
    
    # Metadata from source
    source_metadata = Column(JSONB)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="product_mappings")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("source", "source_product_id", name="uq_product_mapping_source"),
        Index("idx_product_mappings_product_id", "product_id"),
        Index("idx_product_mappings_source", "source", "source_product_id"),
    )


class Order(Base):
    """Unified order header data from all sources"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    
    # Source tracking
    source = Column(SQLEnum(OrderSourceEnum), nullable=False)
    source_order_id = Column(String(255), nullable=False)
    
    # Location
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    
    # Order type
    order_type = Column(SQLEnum(OrderTypeEnum), nullable=False)
    status = Column(SQLEnum(OrderStatusEnum), default=OrderStatusEnum.COMPLETED)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False)
    closed_at = Column(DateTime(timezone=True))
    
    # Business date
    business_date = Column(Date, nullable=False)
    
    # Amounts (all in dollars)
    subtotal = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)
    tip_amount = Column(Numeric(10, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Delivery-specific fields
    delivery_fee = Column(Numeric(10, 2))
    service_fee = Column(Numeric(10, 2))
    commission_fee = Column(Numeric(10, 2))
    
    # Customer info
    customer_name = Column(String(255))
    customer_phone = Column(String(50))
    
    # Staff info
    server_name = Column(String(255))
    
    # Flags
    is_voided = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    contains_alcohol = Column(Boolean, default=False)
    is_catering = Column(Boolean, default=False)
    
    # Source-specific metadata
    source_metadata = Column(JSONB)
    
    # Audit
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    location = relationship("Location", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    delivery_order = relationship("DeliveryOrder", back_populates="order", uselist=False, cascade="all, delete-orphan")
    toast_checks = relationship("ToastCheck", back_populates="order", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("source", "source_order_id", name="uq_order_source"),
        Index("idx_orders_location_id", "location_id"),
        Index("idx_orders_created_at", "created_at"),
        Index("idx_orders_business_date", "business_date"),
        Index("idx_orders_source", "source"),
        Index("idx_orders_source_order_id", "source", "source_order_id"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_order_type", "order_type"),
        Index("idx_orders_location_date", "location_id", "business_date"),
        Index("idx_orders_location_date_status", "location_id", "business_date", "status"),
        Index("idx_orders_source_created", "source", "created_at"),
    )


class OrderItem(Base):
    """Individual line items within orders"""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    
    # Parent order
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    
    # Product reference
    product_id = Column(Integer, ForeignKey("products.id"))
    
    # Item details (denormalized)
    item_name = Column(String(255), nullable=False)
    item_description = Column(Text)
    
    # Quantity and pricing
    quantity = Column(Numeric(10, 3), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    
    # Tax and discount
    tax_amount = Column(Numeric(10, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)
    
    # Item sequence
    sequence_number = Column(Integer)
    
    # Category (denormalized)
    category_name = Column(String(255))
    
    # Source-specific item ID
    source_item_id = Column(String(255))
    
    # Special instructions
    special_instructions = Column(Text)
    
    # Source metadata
    source_metadata = Column(JSONB)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    modifiers = relationship("OrderItemModifier", back_populates="order_item", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_order_items_order_id", "order_id"),
        Index("idx_order_items_product_id", "product_id"),
        Index("idx_order_items_category_name", "category_name"),
        Index("idx_order_items_order_product", "order_id", "product_id"),
        Index("idx_order_items_source_metadata", "source_metadata", postgresql_using="gin"),
    )


class OrderItemModifier(Base):
    """Modifiers/customizations for order items"""
    __tablename__ = "order_item_modifiers"

    id = Column(Integer, primary_key=True)
    
    # Parent order item
    order_item_id = Column(Integer, ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False)
    
    # Modifier details
    modifier_name = Column(String(255), nullable=False)
    modifier_value = Column(String(255))
    
    # Price impact
    price_adjustment = Column(Numeric(10, 2), default=0)
    
    # Quantity
    quantity = Column(Integer, default=1)
    
    # Source-specific modifier ID
    source_modifier_id = Column(String(255))
    
    # Metadata
    extra_data = Column(JSONB)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    order_item = relationship("OrderItem", back_populates="modifiers")
    
    # Indexes
    __table_args__ = (
        Index("idx_order_item_modifiers_order_item_id", "order_item_id"),
    )


class Payment(Base):
    """Payment transactions for orders"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    
    # Parent order
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    
    # Source tracking
    source = Column(SQLEnum(OrderSourceEnum), nullable=False)
    source_payment_id = Column(String(255))
    
    # Payment details
    payment_type = Column(SQLEnum(PaymentTypeEnum), nullable=False)
    status = Column(SQLEnum(PaymentStatusEnum), default=PaymentStatusEnum.COMPLETED)
    
    # Amounts (in dollars)
    amount = Column(Numeric(10, 2), nullable=False)
    tip_amount = Column(Numeric(10, 2), default=0)
    processing_fee = Column(Numeric(10, 2), default=0)
    
    # Timestamp
    processed_at = Column(DateTime(timezone=True), nullable=False)
    
    # Card details
    card_brand = Column(String(50))
    card_last4 = Column(String(4))
    card_entry_method = Column(String(50))
    
    # Digital wallet details
    wallet_brand = Column(String(50))
    
    # Cash details
    cash_tendered = Column(Numeric(10, 2))
    change_amount = Column(Numeric(10, 2))
    
    # Refund tracking
    refund_amount = Column(Numeric(10, 2), default=0)
    refund_date = Column(DateTime(timezone=True))
    refund_reason = Column(Text)
    
    # Source metadata
    source_metadata = Column(JSONB)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="payments")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("source", "source_payment_id", name="uq_payment_source"),
        Index("idx_payments_order_id", "order_id"),
        Index("idx_payments_payment_type", "payment_type"),
        Index("idx_payments_card_brand", "card_brand"),
        Index("idx_payments_status", "status"),
        Index("idx_payments_processed_at", "processed_at"),
    )


class DeliveryOrder(Base):
    """Delivery-specific data (DoorDash)"""
    __tablename__ = "delivery_orders"

    id = Column(Integer, primary_key=True)
    
    # Parent order
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Delivery address
    delivery_address_line1 = Column(String(255))
    delivery_address_line2 = Column(String(255))
    delivery_city = Column(String(100))
    delivery_state = Column(String(50))
    delivery_zip_code = Column(String(20))
    
    # Delivery times
    pickup_time = Column(DateTime(timezone=True))
    delivery_time = Column(DateTime(timezone=True))
    estimated_delivery_time = Column(DateTime(timezone=True))
    
    # Delivery details
    delivery_instructions = Column(Text)
    dasher_name = Column(String(255))
    dasher_id = Column(String(255))
    
    # Delivery fees
    delivery_fee = Column(Numeric(10, 2))
    dasher_tip = Column(Numeric(10, 2))
    
    # Metadata
    extra_data = Column(JSONB)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="delivery_order")
    
    # Indexes
    __table_args__ = (
        Index("idx_delivery_orders_order_id", "order_id"),
        Index("idx_delivery_orders_pickup_time", "pickup_time"),
        Index("idx_delivery_orders_delivery_time", "delivery_time"),
    )


class ToastCheck(Base):
    """Toast-specific check (split bill) data"""
    __tablename__ = "toast_checks"

    id = Column(Integer, primary_key=True)
    
    # Parent order
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    
    # Source tracking
    source_check_id = Column(String(255), nullable=False)
    
    # Check details
    check_number = Column(Integer)
    table_name = Column(String(100))
    
    # Timestamps
    opened_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    
    # Amounts
    subtotal = Column(Numeric(10, 2))
    tax_amount = Column(Numeric(10, 2))
    tip_amount = Column(Numeric(10, 2))
    total_amount = Column(Numeric(10, 2))
    
    # Server info
    server_name = Column(String(255))
    
    # Metadata
    extra_data = Column(JSONB)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="toast_checks")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("source_check_id", name="uq_toast_check_source"),
        Index("idx_toast_checks_order_id", "order_id"),
        Index("idx_toast_checks_opened_at", "opened_at"),
        Index("idx_toast_checks_closed_at", "closed_at"),
    )

