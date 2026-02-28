from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, send_file
from .models import db, User, Donor, BloodRequest, Report
from .utils import find_nearby_donors, calculate_donor_reliability_score, get_blood_compatibility, geocode_address
from functools import wraps
from datetime import datetime, date


def calculate_ai_score(distance, reliability, urgency):
    return (3 * urgency) + (2 * reliability) - (distance / 10)
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
donor_bp = Blueprint('donor', __name__)
search_bp = Blueprint('search', __name__)
admin_bp = Blueprint('admin', __name__)

def login_required(f):
    """Decorator to check if user is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to check if user is admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            return jsonify({'error': 'Forbidden'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@main_bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@main_bp.route('/register')
def register_page():
    """Registration page"""
    return render_template('register.html')

@main_bp.route('/login')
def login_page():
    """Login page"""
    return render_template('login.html')

@main_bp.route('/dashboard')
def dashboard():
    """User dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('main.login_page'))
    return render_template('dashboard.html')

@main_bp.route('/search')
def search_page():
    """Search donors page"""
    return render_template('search.html')

@main_bp.route('/admin/hospitals')
def admin_hospitals():
    """Admin hospital management page"""
    if 'user_id' not in session:
        return redirect(url_for('main.login_page'))
    
    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return redirect(url_for('main.dashboard'))
    
    return render_template('admin_hospitals.html')
@main_bp.route('/admin/donors')
def admin_donors():
    if 'user_id' not in session:
        return redirect(url_for('main.login_page'))

    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return redirect(url_for('main.dashboard'))

    donors = Donor.query.all()

    return render_template('admin_donors.html', donors=donors)


@main_bp.route('/admin/requests')
def admin_requests():
    if 'user_id' not in session:
        return redirect(url_for('main.login_page'))

    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return redirect(url_for('main.dashboard'))

    requests = BloodRequest.query.order_by(BloodRequest.request_id.desc()).all()

    return render_template('admin_requests.html', requests=requests)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register new user"""
    try:
        data = request.get_json()
        
        if not all([data.get('name'), data.get('email'), data.get('password'), data.get('phone')]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        phone = data.get('phone', '').replace('-', '').replace(' ', '')
        if not phone.isdigit() or len(phone) != 10:
            return jsonify({'error': 'Phone must be exactly 10 digits'}), 400
        password = data.get('password', '')
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        if not any(c.isupper() for c in password):
            return jsonify({'error': 'Password must contain at least 1 uppercase letter'}), 400
        if not any(c in '!@#$%^&*()_+-=[]{};\':"|,.<>?\/' for c in password):
            return jsonify({'error': 'Password must contain at least 1 special character'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        user = User(
            name=data['name'],
            email=data['email'],
            phone=phone,
            gender=data.get('gender'),
            role=data.get('role', 'donor')
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        if user.role == 'donor':
            donor = Donor(
                user_id=user.user_id,
                blood_group=data.get('blood_group', ''),
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                address=data.get('address', ''),
                city=data.get('city', '')
            )
            db.session.add(donor)
            db.session.commit()
        
        session['user_id'] = user.user_id
        
        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()

        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Missing email or password'}), 400

        user = User.query.filter_by(email=data['email']).first()

        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401

        session['user_id'] = user.user_id

        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout"""
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/current-user', methods=['GET'])
@login_required
def current_user():
    """Get current user info"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user_data = user.to_dict()
    if user.donor_profile:
        user_data['donor'] = user.donor_profile.to_dict()
    
    return jsonify(user_data), 200

@donor_bp.route('/donors', methods=['GET'])
def get_donors():
    """Get all donors with pagination and filters"""
    try:
        page = request.args.get('page', 1, type=int)
        blood_group = request.args.get('blood_group')
        city = request.args.get('city')
        
        query = Donor.query.filter_by(is_available=True)
        
        if blood_group:
            query = query.filter_by(blood_group=blood_group)
        
        if city:
            query = query.filter_by(city=city)
        
        donors = query.paginate(page=page, per_page=10)
        
        return jsonify({
            'donors': [d.to_dict() for d in donors.items],
            'total': donors.total,
            'pages': donors.pages
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@donor_bp.route('/donors/<int:donor_id>', methods=['GET'])
def get_donor(donor_id):
    """Get specific donor"""
    try:
        donor = Donor.query.get(donor_id)
        
        if not donor:
            return jsonify({'error': 'Donor not found'}), 404
        
        return jsonify(donor.to_dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@donor_bp.route('/donors/<int:donor_id>', methods=['PUT'])
@login_required
def update_donor(donor_id):
    """Update donor profile"""
    try:
        donor = Donor.query.get(donor_id)
        
        if not donor or donor.user_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        if 'blood_group' in data:
            donor.blood_group = data['blood_group']
        if 'latitude' in data:
            donor.latitude = data['latitude']
        if 'longitude' in data:
            donor.longitude = data['longitude']
        if 'address' in data:
            donor.address = data['address']
        if 'city' in data:
            donor.city = data['city']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Donor profile updated',
            'donor': donor.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@donor_bp.route('/donors/<int:donor_id>/availability', methods=['PATCH'])
@login_required
def toggle_availability(donor_id):
    """Toggle donor availability"""
    try:
        donor = Donor.query.get(donor_id)
        
        if not donor or donor.user_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        donor.is_available = data.get('is_available', not donor.is_available)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Availability updated',
            'donor': donor.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@search_bp.route('/search', methods=['POST'])
def search():
    """Search donors by blood group and location"""
    try:
        data = request.get_json() or {}

        patient_group = data.get('blood_group')

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        location_text = data.get('location')
        radius_km = float(data.get('radius_km', 10))

        if (latitude is None or longitude is None) and location_text:
            lat, lon = geocode_address(location_text)
            latitude = latitude or lat
            longitude = longitude or lon

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return jsonify({'error': 'Missing or invalid coordinates'}), 400

        donors = find_nearby_donors(patient_group, latitude, longitude, radius_km)


        results = []
        urgency_level = data.get('urgency', 2)

        for d in donors:
            donor_obj = Donor.query.get(d['donor_id'])
            if donor_obj:
                reliability = calculate_donor_reliability_score(donor_obj)
            else:
                reliability = 50

            distance = d.get('distance_km', 0)
            ai_score = calculate_ai_score(distance, reliability, urgency_level)

            d['reliability_score'] = reliability
            d['ai_score'] = round(ai_score, 2)

            results.append(d)

        results.sort(key=lambda x: x['ai_score'], reverse=True)

        return jsonify({
            'donors': results,
            'count': len(results)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@search_bp.route('/donors/nearby', methods=['GET'])
def get_nearby_donors():
    """Get nearby donors (alternative endpoint)"""
    try:
        latitude = request.args.get('latitude')
        longitude = request.args.get('longitude')
        location_text = request.args.get('location')
        blood_group = request.args.get('blood_group')
        radius_km = float(request.args.get('radius_km', 10))

        if (not latitude or not longitude) and location_text:
            lat, lon = geocode_address(location_text)
            latitude = latitude or lat
            longitude = longitude or lon

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return jsonify({'error': 'Missing or invalid coordinates'}), 400

        donors = find_nearby_donors(blood_group, latitude, longitude, radius_km)
        return jsonify(donors), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@search_bp.route('/requests', methods=['POST'])
@login_required
def create_request():
    """Create blood request"""
    try:
        data = request.get_json()
        
        blood_request = BloodRequest(
            requester_id=session['user_id'],
            blood_group=data.get('blood_group'),
            urgency_level=data.get('urgency_level', 'normal'),
            location=data.get('location'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude')
        )
        
        db.session.add(blood_request)
        db.session.commit()
        
        return jsonify({
            'message': 'Blood request created',
            'request': blood_request.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@search_bp.route('/requests/<int:request_id>', methods=['GET'])
def get_request(request_id):
    """Get blood request details"""
    try:
        blood_request = BloodRequest.query.get(request_id)
        
        if not blood_request:
            return jsonify({'error': 'Request not found'}), 404
        
        return jsonify(blood_request.to_dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@search_bp.route('/requests/<int:request_id>', methods=['PUT'])
@login_required
def update_request(request_id):
    """Update blood request"""
    try:
        blood_request = BloodRequest.query.get(request_id)
        
        if not blood_request or blood_request.requester_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        if 'status' in data:
            blood_request.status = data['status']
        if 'urgency_level' in data:
            blood_request.urgency_level = data['urgency_level']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Request updated',
            'request': blood_request.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
def get_users():
    """Get all users (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        role = request.args.get('role')
        
        from sqlalchemy import or_

        query = User.query.filter(
    or_(User.role == 'donor', User.role == 'seeker')
)
        if role:
            query = query.filter_by(role=role)
        
        users = query.paginate(page=page, per_page=10)
        
        return jsonify({
            'users': [u.to_dict() for u in users.items],
            'total': users.total,
            'pages': users.pages
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update user details (admin only)"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            user.email = data['email']
        if 'is_verified' in data:
            user.is_verified = data['is_verified']
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete user (admin only)"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'User deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/verify/<int:user_id>', methods=['POST'])
@admin_required
def verify_user(user_id):
    """Verify user (admin only)"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.is_verified = True
        db.session.commit()
        
        return jsonify({
            'message': 'User verified',
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/reports', methods=['GET'])
@admin_required
def get_reports():
    """Get all reports (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status')
        
        query = Report.query
        if status:
            query = query.filter_by(status=status)
        
        reports = query.paginate(page=page, per_page=10)
        
        return jsonify({
            'reports': [r.to_dict() for r in reports.items],
            'total': reports.total,
            'pages': reports.pages
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/reports/<int:report_id>', methods=['PUT'])
@admin_required
def handle_report(report_id):
    """Handle report (admin only)"""
    try:
        report = Report.query.get(report_id)
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        data = request.get_json()
        report.status = data.get('status', 'pending')
        
        db.session.commit()
        
        return jsonify({
            'message': 'Report updated',
            'report': report.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/reports', methods=['POST'])
@login_required
def create_report():
    """Create report about user"""
    try:
        data = request.get_json()
        
        report = Report(
            reporter_id=session['user_id'],
            reported_user_id=data.get('reported_user_id'),
            reason=data.get('reason')
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'message': 'Report submitted',
            'report': report.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
