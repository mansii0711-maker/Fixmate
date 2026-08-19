from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'customer', 'provider', 'admin'
    status = db.Column(db.String(20), default='Approved')  # 'Approved', 'Pending', 'Rejected'
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    customer_profile = db.relationship('CustomerProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    provider_profile = db.relationship('ProviderProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'mobile': self.mobile,
            'address': self.address,
            'role': self.role,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

class CustomerProfile(db.Model):
    __tablename__ = 'customer_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    default_location = db.Column(db.String(100), nullable=True)

class ProviderProfile(db.Model):
    __tablename__ = 'provider_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    experience = db.Column(db.Integer, nullable=False, default=0) # years
    qualification = db.Column(db.String(150), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    operating_area = db.Column(db.String(100), nullable=False)
    verification_doc = db.Column(db.String(255), nullable=True)
    photo = db.Column(db.String(255), nullable=True, default='default_avatar.png')
    bio = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Float, default=5.0)
    total_reviews = db.Column(db.Integer, default=0)

    category = db.relationship('Category', backref='providers')
    services = db.relationship('Service', backref='provider', lazy=True, cascade="all, delete-orphan")

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    slug = db.Column(db.String(80), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), default='fa-tools')
    
    services = db.relationship('Service', backref='category', lazy=True)

class Service(db.Model):
    __tablename__ = 'services'
    
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('provider_profiles.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    price_type = db.Column(db.String(20), default='Fixed') # 'Fixed', 'Per Hour', 'Per Visit'
    estimated_time = db.Column(db.String(50), default='1-2 Hours')
    image = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id', ondelete='CASCADE'), nullable=False)
    booking_date = db.Column(db.String(20), nullable=False)
    time_slot = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), default='Pending') # 'Pending', 'Confirmed', 'Completed', 'Cancelled'
    payment_status = db.Column(db.String(20), default='Pending') # 'Pending', 'Paid'
    payment_method = db.Column(db.String(50), default='Cash After Service') # 'Cash After Service', 'Razorpay Test Mode'
    total_amount = db.Column(db.Float, nullable=False)
    address = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    # Razorpay Transaction Audit Attributes
    razorpay_order_id = db.Column(db.String(100), nullable=True)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    razorpay_signature = db.Column(db.String(255), nullable=True)
    payment_amount = db.Column(db.Float, nullable=True)
    payment_currency = db.Column(db.String(10), default='INR')
    payment_timestamp = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now)

    customer = db.relationship('User', foreign_keys=[customer_id], backref='customer_bookings')
    provider = db.relationship('User', foreign_keys=[provider_id], backref='provider_bookings')
    service = db.relationship('Service', backref='bookings')

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    customer = db.relationship('User', foreign_keys=[customer_id])
    provider = db.relationship('User', foreign_keys=[provider_id])

class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='notifications')

