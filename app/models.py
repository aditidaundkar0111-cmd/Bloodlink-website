from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt

db = SQLAlchemy()

class User(db.Model):
    """User model for both donors and blood seekers"""
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    role = db.Column(db.String(20), default='donor')  
    gender = db.Column(db.String(20))  
    age = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    donor_profile = db.relationship('Donor', uselist=False, backref='user', cascade='all, delete-orphan')
    requests_created = db.relationship('BloodRequest', foreign_keys='BloodRequest.requester_id', backref='requester', cascade='all, delete-orphan')
    reports_filed = db.relationship('Report', foreign_keys='Report.reporter_id', backref='reporter', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Check if password matches hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'gender': self.gender,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat()
        }

class Donor(db.Model):
    """Donor profile model"""
    __tablename__ = 'donors'
    
    donor_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    blood_group = db.Column(db.String(5), nullable=False)  # A+, A-, B+, B-, O+, O-, AB+, AB-
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    is_available = db.Column(db.Boolean, default=True)
    last_donation_date = db.Column(db.Date)
    donation_count = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'donor_id': self.donor_id,
            'user_id': self.user_id,
            'name': self.user.name,
            'email': self.user.email,
            'phone': self.user.phone,
            'blood_group': self.blood_group,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'address': self.address,
            'city': self.city,
            'is_available': self.is_available,
            'last_donation_date': self.last_donation_date.isoformat() if self.last_donation_date else None,
            'donation_count': self.donation_count,
            'is_verified': self.user.is_verified
        }

class BloodRequest(db.Model):
    """Blood request model"""
    __tablename__ = 'blood_requests'
    
    request_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    blood_group = db.Column(db.String(5), nullable=False)
    urgency_level = db.Column(db.String(20), default='normal')  # 'critical', 'urgent', 'normal'
    location = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    status = db.Column(db.String(20), default='active')  # 'active', 'fulfilled', 'cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'request_id': self.request_id,
            'requester_id': self.requester_id,
            'requester_name': self.requester.name,
            'requester_phone': self.requester.phone,
            'blood_group': self.blood_group,
            'urgency_level': self.urgency_level,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

class Report(db.Model):
    """Report model for spam/abuse reporting"""
    __tablename__ = 'reports'
    
    report_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reported_user = db.relationship('User', foreign_keys=[reported_user_id], backref='reports_against')
    
    def to_dict(self):
        return {
            'report_id': self.report_id,
            'reporter_id': self.reporter_id,
            'reported_user_id': self.reported_user_id,
            'reported_user_name': self.reported_user.name,
            'reason': self.reason,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }