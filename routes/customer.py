from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, current_app
from flask_login import login_required, current_user, logout_user
from database import db, User, CustomerProfile, ProviderProfile, Category, Service, Booking, Review, Notification
from werkzeug.security import generate_password_hash
from datetime import date, datetime
import re, hmac, hashlib, time, json, base64
import urllib.request
import urllib.error

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

@customer_bp.before_request
@login_required
def check_customer_role():
    if current_user.role != 'customer':
        flash('Access restricted to Customer accounts.', 'danger')
        return redirect(url_for('public.home'))

    if current_user.status == 'Suspended':
        logout_user()
        flash('Your account has been suspended by Administration. Access revoked.', 'danger')
        return redirect(url_for('auth.login'))

# 0. Location Selection Onboarding Page (After Login)
@customer_bp.route('/select-location', methods=['GET', 'POST'])
def select_location():
    if request.method == 'POST':
        area = request.form.get('area', '').strip()
        if area:
            session['user_location'] = area
            if current_user.is_authenticated and current_user.role == 'customer':
                if not current_user.customer_profile:
                    cp = CustomerProfile(user_id=current_user.id, default_location=area)
                    db.session.add(cp)
                else:
                    current_user.customer_profile.default_location = area
                db.session.commit()

            flash(f'Default location updated to "{area}". Services near you will be shown automatically!', 'success')
            return redirect(url_for('customer.dashboard'))
        else:
            flash('Please select or detect your location to proceed.', 'warning')
            return redirect(url_for('customer.select_location'))

    operating_areas = get_operating_areas()
    return render_template('customer/select_location.html', operating_areas=operating_areas)

# 1. Customer Dashboard Overview
@customer_bp.route('/dashboard')
def dashboard():
    bookings = Booking.query.filter_by(customer_id=current_user.id).order_by(Booking.created_at.desc()).all()
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()

    stats = {
        'total_bookings': len(bookings),
        'pending_bookings': len([b for b in bookings if b.status == 'Pending']),
        'confirmed_bookings': len([b for b in bookings if b.status == 'Confirmed']),
        'completed_bookings': len([b for b in bookings if b.status == 'Completed'])
    }
    
    recent_bookings = bookings[:5]
    
    return render_template('customer/dashboard.html', 
                           stats=stats, 
                           recent_bookings=recent_bookings, 
                           notifications=notifications,
                           active_page='dashboard')

# 2. Customer Profile Management
@customer_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        address = request.form.get('address', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not full_name or not mobile or not address:
            flash('Name, Mobile, and Address cannot be empty.', 'danger')
            return redirect(url_for('customer.profile'))

        if not re.match(r'^[a-zA-Z\s]{3,50}$', full_name):
            flash('Full Name must contain only letters and spaces.', 'danger')
            return redirect(url_for('customer.profile'))

        clean_mobile = re.sub(r'[\s\-\(\)\+]', '', mobile)
        if clean_mobile.startswith('91') and len(clean_mobile) == 12:
            clean_mobile = clean_mobile[2:]
        elif clean_mobile.startswith('0') and len(clean_mobile) == 11:
            clean_mobile = clean_mobile[1:]

        if not re.match(r'^[6-9]\d{9}$', clean_mobile):
            flash('Please enter a valid 10-digit Indian mobile number.', 'danger')
            return redirect(url_for('customer.profile'))

        current_user.full_name = full_name
        current_user.mobile = clean_mobile
        current_user.address = address

        if new_password:
            if len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
                return redirect(url_for('customer.profile'))
            if new_password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return redirect(url_for('customer.profile'))
            current_user.set_password(new_password)

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('customer.profile'))

    return render_template('customer/profile.html', active_page='profile')

def get_operating_areas():
    all_areas_raw = db.session.query(ProviderProfile.operating_area).join(User).filter(User.status == 'Approved').all()
    areas_set = set()
    for row in all_areas_raw:
        if row[0]:
            for a in row[0].split(','):
                clean = a.strip()
                if clean:
                    areas_set.add(clean)
    return sorted(list(areas_set))

# 3. Customer Search Services Page (Category, Area, Price, Rating Filters)
@customer_bp.route('/services')
def search_services():
    category_slug = request.args.get('category', '')
    area_query = request.args.get('area')
    if area_query is None:
        area_query = session.get('user_location', '')
    else:
        area_query = area_query.strip()
    max_price = request.args.get('max_price', '')
    min_rating = request.args.get('min_rating', '')

    query = Service.query.join(ProviderProfile).join(User).filter(User.status == 'Approved', Service.is_active == True)

    if category_slug:
        cat = Category.query.filter_by(slug=category_slug).first()
        if cat:
            query = query.filter(Service.category_id == cat.id)

    if area_query:
        query = query.filter(ProviderProfile.operating_area.ilike(f'%{area_query}%'))

    if max_price and max_price.isdigit():
        query = query.filter(Service.price <= float(max_price))

    if min_rating:
        try:
            query = query.filter(ProviderProfile.rating >= float(min_rating))
        except ValueError:
            pass

    services_list = query.all()
    categories = Category.query.all()
    operating_areas = get_operating_areas()

    return render_template('customer/services.html', 
                           services=services_list, 
                           categories=categories,
                           operating_areas=operating_areas,
                           selected_category=category_slug,
                           area_query=area_query,
                           max_price=max_price,
                           min_rating=min_rating,
                           active_page='search_services')

# 4. Service Details View & Booking Modal Trigger
@customer_bp.route('/services/<int:service_id>')
def service_detail(service_id):
    service = Service.query.get_or_404(service_id)
    provider_user = User.query.get(service.provider.user_id)
    reviews = Review.query.filter_by(provider_id=provider_user.id).order_by(Review.created_at.desc()).all()

    time_slots = [
        '09:00 AM - 11:00 AM',
        '11:00 AM - 01:00 PM',
        '02:00 PM - 04:00 PM',
        '04:00 PM - 06:00 PM',
        '06:00 PM - 08:00 PM'
    ]

    today_date = date.today().strftime('%Y-%m-%d')

    return render_template('customer/service_detail.html', 
                           service=service, 
                           provider=provider_user, 
                           reviews=reviews, 
                           time_slots=time_slots,
                           today_date=today_date,
                           active_page='search_services')

# 5. Step 1: Initiate Booking & Save Pending Session Details (With Double Booking Check)
@customer_bp.route('/book/<int:service_id>', methods=['POST'])
def book_service(service_id):
    service = Service.query.get_or_404(service_id)
    booking_date = request.form.get('booking_date')
    time_slot = request.form.get('time_slot')
    address = request.form.get('address', current_user.address)
    notes = request.form.get('notes', '')

    if not booking_date or not time_slot:
        flash('Please select both date and time slot for booking.', 'warning')
        return redirect(url_for('customer.service_detail', service_id=service_id))

    # Prevent double booking for the same provider, date, and time slot
    existing_booking = Booking.query.filter(
        Booking.provider_id == service.provider.user_id,
        Booking.booking_date == booking_date,
        Booking.time_slot == time_slot,
        Booking.status != 'Cancelled'
    ).first()

    if existing_booking:
        flash(f'The time slot ({time_slot}) on {booking_date} is already booked for this provider. Please select a different time slot or date.', 'danger')
        return redirect(url_for('customer.service_detail', service_id=service_id))

    service_charge = float(service.price)
    platform_fee = 50.0
    discount = 0.0
    total_payable = service_charge + platform_fee - discount

    session['pending_booking'] = {
        'service_id': service.id,
        'booking_date': booking_date,
        'time_slot': time_slot,
        'address': address,
        'notes': notes,
        'service_charge': service_charge,
        'platform_fee': platform_fee,
        'discount': discount,
        'total_payable': total_payable
    }

    return redirect(url_for('customer.booking_summary'))

# 5a. Step 2: Booking Summary Page
@customer_bp.route('/booking-summary')
def booking_summary():
    pending = session.get('pending_booking')
    if not pending:
        flash('No active booking in progress. Please select a service to book.', 'warning')
        return redirect(url_for('customer.search_services'))

    service = Service.query.get_or_404(pending['service_id'])
    provider_user = User.query.get(service.provider.user_id)

    return render_template('customer/booking_summary.html',
                           service=service,
                           provider=provider_user,
                           pending=pending,
                           active_page='search_services')

# 5b. Step 3: Select Payment Method Page
@customer_bp.route('/booking-payment')
def booking_payment():
    pending = session.get('pending_booking')
    if not pending:
        flash('No active booking session found.', 'warning')
        return redirect(url_for('customer.search_services'))

    service = Service.query.get_or_404(pending['service_id'])
    razorpay_key_id = current_app.config.get('RAZORPAY_KEY_ID', '')

    return render_template('customer/booking_payment.html',
                           service=service,
                           pending=pending,
                           razorpay_key_id=razorpay_key_id,
                           active_page='search_services')

# 5c-1. Razorpay Order Creation Endpoint (Server-Side)
@customer_bp.route('/create-razorpay-order', methods=['POST'])
def create_razorpay_order():
    pending = session.get('pending_booking')
    if not pending:
        return jsonify({'success': False, 'message': 'Booking session expired. Please re-select your service.'}), 400

    service = Service.query.get_or_404(pending['service_id'])

    # Always compute price strictly on server from database (Never trust frontend amount)
    service_charge = float(service.price)
    platform_fee = 50.0
    discount = 0.0
    total_payable = service_charge + platform_fee - discount
    pending['total_payable'] = total_payable
    session['pending_booking'] = pending

    # Convert INR to paise
    amount_in_paise = int(round(total_payable * 100))

    key_id = current_app.config.get('RAZORPAY_KEY_ID', '')
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET', '')

    if not key_id or not key_secret:
        return jsonify({'success': False, 'message': 'Razorpay API credentials (RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET) missing in .env file.'}), 400

    # Official Razorpay Orders REST API call
    try:
        auth_bytes = f"{key_id}:{key_secret}".encode('utf-8')
        auth_header = "Basic " + base64.b64encode(auth_bytes).decode('utf-8')
        
        req_data = json.dumps({
            'amount': amount_in_paise,
            'currency': 'INR',
            'receipt': f'receipt_fix_{int(time.time())}',
            'notes': {
                'service_title': service.title,
                'customer_id': str(current_user.id)
            }
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.razorpay.com/v1/orders',
            data=req_data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': auth_header
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8')
            order_data = json.loads(res_body)
            order_id = order_data['id']
            pending['razorpay_order_id'] = order_id
            session['pending_booking'] = pending
            return jsonify({
                'success': True,
                'order_id': order_id,
                'amount': amount_in_paise,
                'currency': 'INR',
                'key_id': key_id,
                'customer_name': current_user.full_name,
                'customer_email': current_user.email,
                'customer_phone': current_user.mobile or ''
            })
    except urllib.error.HTTPError as err:
        err_msg = err.read().decode('utf-8') if err.fp else str(err)
        return jsonify({'success': False, 'message': f'Razorpay Order creation error: {err_msg}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Razorpay API Connection Error: {str(e)}'}), 500

# 5c-2. Razorpay Signature Verification Endpoint (Server-Side)
@customer_bp.route('/verify-razorpay-payment', methods=['POST'])
def verify_razorpay_payment():
    pending = session.get('pending_booking')
    if not pending:
        return jsonify({'success': False, 'message': 'Booking session expired. Please try booking again.'}), 400

    data = request.get_json() or {}
    razorpay_payment_id = data.get('razorpay_payment_id', '')
    razorpay_order_id = data.get('razorpay_order_id', '')
    razorpay_signature = data.get('razorpay_signature', '')

    if not razorpay_payment_id or not razorpay_order_id or not razorpay_signature:
        return jsonify({'success': False, 'message': 'Missing transaction tokens or signature.'}), 400

    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET', '')
    if not key_secret:
        return jsonify({'success': False, 'message': 'Razorpay secret key not configured.'}), 400

    # Strict Server-side HMAC SHA-256 signature verification
    message = f"{razorpay_order_id}|{razorpay_payment_id}"
    generated_signature = hmac.new(
        key_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(generated_signature, razorpay_signature):
        return jsonify({'success': False, 'message': 'Razorpay signature verification failed! Payment rejected.'}), 400

    service = Service.query.get_or_404(pending['service_id'])

    # Concurrency double-booking check
    existing_booking = Booking.query.filter(
        Booking.provider_id == service.provider.user_id,
        Booking.booking_date == pending['booking_date'],
        Booking.time_slot == pending['time_slot'],
        Booking.status != 'Cancelled'
    ).first()

    if existing_booking:
        session.pop('pending_booking', None)
        return jsonify({'success': False, 'message': f'The time slot ({pending["time_slot"]}) on {pending["booking_date"]} was just booked by another customer.'}), 400

    # Save confirmed paid booking
    new_booking = Booking(
        customer_id=current_user.id,
        provider_id=service.provider.user_id,
        service_id=service.id,
        booking_date=pending['booking_date'],
        time_slot=pending['time_slot'],
        status='Confirmed',
        payment_status='Paid',
        payment_method='Razorpay Test Mode',
        total_amount=pending['total_payable'],
        address=pending['address'],
        notes=pending['notes'],
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
        payment_amount=pending['total_payable'],
        payment_currency='INR',
        payment_timestamp=datetime.now()
    )
    db.session.add(new_booking)
    db.session.flush()

    # Create notifications
    notif_cust = Notification(
        user_id=current_user.id,
        title=f'Booking Confirmed (#FIX-{new_booking.id})',
        message=f'Your booking for "{service.title}" on {pending["booking_date"]} ({pending["time_slot"]}) is confirmed. Payment: Paid via Razorpay.'
    )
    notif_prov = Notification(
        user_id=service.provider.user_id,
        title=f'New Paid Service Booking (#FIX-{new_booking.id})',
        message=f'Customer {current_user.full_name} booked "{service.title}" for {pending["booking_date"]} ({pending["time_slot"]}). Payment status: Paid.'
    )
    db.session.add(notif_cust)
    db.session.add(notif_prov)
    db.session.commit()

    # Clear pending session
    session.pop('pending_booking', None)

    flash('Payment verified and booking confirmed successfully!', 'success')
    return jsonify({
        'success': True,
        'redirect_url': url_for('customer.booking_confirmation', booking_id=new_booking.id)
    })

# 5c-3. Process Cash After Service Payment
@customer_bp.route('/process-booking-payment', methods=['POST'])
def process_booking_payment():
    pending = session.get('pending_booking')
    if not pending:
        flash('Booking session expired. Please try booking again.', 'danger')
        return redirect(url_for('customer.search_services'))

    payment_method = request.form.get('payment_method', 'Cash After Service')
    service = Service.query.get_or_404(pending['service_id'])

    # Double check no collision occurred during summary/payment selection
    existing_booking = Booking.query.filter(
        Booking.provider_id == service.provider.user_id,
        Booking.booking_date == pending['booking_date'],
        Booking.time_slot == pending['time_slot'],
        Booking.status != 'Cancelled'
    ).first()

    if existing_booking:
        session.pop('pending_booking', None)
        flash(f'The time slot ({pending["time_slot"]}) on {pending["booking_date"]} was just booked by another user. Please select a different time slot or date.', 'danger')
        return redirect(url_for('customer.service_detail', service_id=service.id))

    new_booking = Booking(
        customer_id=current_user.id,
        provider_id=service.provider.user_id,
        service_id=service.id,
        booking_date=pending['booking_date'],
        time_slot=pending['time_slot'],
        status='Pending',
        payment_status='Pending',
        payment_method='Cash After Service',
        total_amount=pending['total_payable'],
        address=pending['address'],
        notes=pending['notes'],
        payment_amount=pending['total_payable'],
        payment_currency='INR',
        payment_timestamp=datetime.now()
    )
    db.session.add(new_booking)
    db.session.flush()

    # Create notifications for customer and provider
    notif_cust = Notification(
        user_id=current_user.id,
        title=f'Booking Placed (#FIX-{new_booking.id})',
        message=f'Your booking for "{service.title}" on {pending["booking_date"]} ({pending["time_slot"]}) is placed. Payment Method: Cash After Service.'
    )
    notif_prov = Notification(
        user_id=service.provider.user_id,
        title=f'New Service Booking Request (#FIX-{new_booking.id})',
        message=f'Customer {current_user.full_name} booked "{service.title}" for {pending["booking_date"]} ({pending["time_slot"]}). Payment Method: Cash After Service.'
    )
    db.session.add(notif_cust)
    db.session.add(notif_prov)
    db.session.commit()

    # Clear pending session
    session.pop('pending_booking', None)

    flash('Booking completed successfully! Pay cash after service visit.', 'success')
    return redirect(url_for('customer.booking_confirmation', booking_id=new_booking.id))

# 5d. Step 5: Professional Booking Confirmation Page
@customer_bp.route('/booking-confirmation/<int:booking_id>')
def booking_confirmation(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.customer_id != current_user.id:
        flash('Unauthorized access to booking confirmation.', 'danger')
        return redirect(url_for('customer.my_bookings'))

    return render_template('customer/booking_confirmation.html', booking=booking, active_page='my_bookings')

# 6. My Bookings Page
@customer_bp.route('/bookings')
def my_bookings():
    status_filter = request.args.get('status', '')
    query = Booking.query.filter_by(customer_id=current_user.id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
        
    bookings = query.order_by(Booking.created_at.desc()).all()
    
    return render_template('customer/bookings.html', bookings=bookings, current_filter=status_filter, active_page='my_bookings')

# 7. Payments Page
@customer_bp.route('/payments')
def payments():
    bookings = Booking.query.filter_by(customer_id=current_user.id).order_by(Booking.created_at.desc()).all()
    completed_payments = [b for b in bookings if b.payment_status == 'Paid']
    pending_payments = [b for b in bookings if b.payment_status == 'Pending' and b.status in ['Confirmed', 'Completed']]

    return render_template('customer/payments.html', 
                           completed_payments=completed_payments, 
                           pending_payments=pending_payments, 
                           active_page='payments')

# 8. Reviews Page
@customer_bp.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if request.method == 'POST':
        booking_id = request.form.get('booking_id')
        rating = request.form.get('rating', 5)
        comment = request.form.get('comment', '').strip()

        booking = Booking.query.get_or_404(booking_id)
        if booking.customer_id != current_user.id or booking.status != 'Completed':
            flash('Invalid booking review attempt.', 'danger')
            return redirect(url_for('customer.reviews'))

        existing_review = Review.query.filter_by(booking_id=booking.id).first()
        if existing_review:
            flash('You have already submitted a review for this booking.', 'warning')
            return redirect(url_for('customer.reviews'))

        new_review = Review(
            booking_id=booking.id,
            customer_id=current_user.id,
            provider_id=booking.provider_id,
            rating=int(rating),
            comment=comment
        )
        db.session.add(new_review)
        
        # Update provider average rating
        provider_prof = ProviderProfile.query.filter_by(user_id=booking.provider_id).first()
        if provider_prof:
            all_prov_reviews = Review.query.filter_by(provider_id=booking.provider_id).all()
            total_revs = len(all_prov_reviews) + 1
            avg_rating = (sum(r.rating for r in all_prov_reviews) + int(rating)) / total_revs
            provider_prof.rating = round(avg_rating, 1)
            provider_prof.total_reviews = total_revs

        db.session.commit()
        flash('Thank you for submitting your review!', 'success')
        return redirect(url_for('customer.reviews'))

    my_reviews = Review.query.filter_by(customer_id=current_user.id).order_by(Review.created_at.desc()).all()
    reviewable_bookings = Booking.query.filter_by(customer_id=current_user.id, status='Completed').all()
    # Exclude already reviewed bookings
    reviewed_booking_ids = [r.booking_id for r in my_reviews]
    pending_review_bookings = [b for b in reviewable_bookings if b.id not in reviewed_booking_ids]

    return render_template('customer/reviews.html', 
                           my_reviews=my_reviews, 
                           pending_review_bookings=pending_review_bookings, 
                           active_page='reviews')

# 9. Notifications Page
@customer_bp.route('/notifications')
def notifications():
    notifications_list = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    # Mark all as read
    for n in notifications_list:
        n.is_read = True
    db.session.commit()

    return render_template('customer/notifications.html', notifications=notifications_list, active_page='notifications')
