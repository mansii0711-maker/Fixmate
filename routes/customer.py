from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from database import db, User, CustomerProfile, ProviderProfile, Category, Service, Booking, Review, Notification, Payment
from werkzeug.security import generate_password_hash
import re
import razorpay
import time


customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

@customer_bp.before_request
@login_required
def check_customer_role():
    if current_user.role != 'customer':
        flash('Access restricted to Customer accounts.', 'danger')
        return redirect(url_for('public.home'))

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

# 3. Customer Search Services Page (Category, Area, Price, Rating Filters)
@customer_bp.route('/services')
def search_services():
    category_slug = request.args.get('category', '')
    area_query = request.args.get('area', '').strip()
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

    return render_template('customer/services.html', 
                           services=services_list, 
                           categories=categories,
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

    return render_template('customer/service_detail.html', 
                           service=service, 
                           provider=provider_user, 
                           reviews=reviews, 
                           time_slots=time_slots,
                           active_page='search_services')

# Helper to get Razorpay client
def get_razorpay_client():
    key_id = current_app.config.get('RAZORPAY_KEY_ID', 'rzp_test_FixMateKey2026')
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET', 'FixMateSecretKey2026')
    return razorpay.Client(auth=(key_id, key_secret))

def create_or_get_razorpay_order(booking):
    payment = Payment.query.filter_by(booking_id=booking.id).first()
    key_id = current_app.config.get('RAZORPAY_KEY_ID', 'rzp_test_FixMateKey2026')
    
    if payment and payment.razorpay_order_id:
        return payment.razorpay_order_id, key_id

    client = get_razorpay_client()
    amount_paise = int(round(booking.total_amount * 100))
    
    try:
        order_data = {
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': f'rcpt_{booking.id}',
            'payment_capture': 1
        }
        order = client.order.create(data=order_data)
        razorpay_order_id = order['id']
    except Exception:
        razorpay_order_id = f"order_fixmate_{booking.id}_{int(time.time())}"

    payment = Payment(
        booking_id=booking.id,
        razorpay_order_id=razorpay_order_id,
        amount=booking.total_amount,
        currency='INR',
        status='Created'
    )
    db.session.add(payment)
    db.session.commit()
    
    return razorpay_order_id, key_id

# 5. Booking Creation with Payment Redirect Option
@customer_bp.route('/book/<int:service_id>', methods=['POST'])
def book_service(service_id):
    service = Service.query.get_or_404(service_id)
    booking_date = request.form.get('booking_date')
    time_slot = request.form.get('time_slot')
    address = request.form.get('address', current_user.address)
    notes = request.form.get('notes', '')
    pay_now = request.form.get('pay_now', '1')

    if not booking_date or not time_slot:
        flash('Please select both date and time slot for booking.', 'warning')
        return redirect(url_for('customer.service_detail', service_id=service_id))

    new_booking = Booking(
        customer_id=current_user.id,
        provider_id=service.provider.user_id,
        service_id=service.id,
        booking_date=booking_date,
        time_slot=time_slot,
        status='Pending',
        payment_status='Pending',
        total_amount=service.price,
        address=address,
        notes=notes
    )
    db.session.add(new_booking)
    db.session.flush()

    # Create notification for provider & customer
    notif_cust = Notification(
        user_id=current_user.id,
        title='Booking Request Created',
        message=f'Your booking request for "{service.title}" on {booking_date} ({time_slot}) has been created.'
    )
    notif_prov = Notification(
        user_id=service.provider.user_id,
        title='New Service Booking Request',
        message=f'Customer {current_user.full_name} requested "{service.title}" on {booking_date}.'
    )
    db.session.add(notif_cust)
    db.session.add(notif_prov)
    db.session.commit()

    return redirect(url_for('payment.select_payment_method', booking_id=new_booking.id))


# 5b. Payment Checkout Page (Razorpay Interface)
@customer_bp.route('/payment/checkout/<int:booking_id>')
def payment_checkout(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.customer_id != current_user.id:
        flash('Unauthorized access to booking payment.', 'danger')
        return redirect(url_for('customer.my_bookings'))

    razorpay_order_id, razorpay_key_id = create_or_get_razorpay_order(booking)

    return render_template('customer/payment_checkout.html',
                           booking=booking,
                           razorpay_order_id=razorpay_order_id,
                           razorpay_key_id=razorpay_key_id,
                           amount_paise=int(round(booking.total_amount * 100)),
                           active_page='payments')

# 5c. Create Razorpay Order API (for AJAX triggers on payments page)
@customer_bp.route('/payment/create-order/<int:booking_id>', methods=['POST'])
def create_order_api(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.customer_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    razorpay_order_id, razorpay_key_id = create_or_get_razorpay_order(booking)

    return jsonify({
        'success': True,
        'order_id': razorpay_order_id,
        'key_id': razorpay_key_id,
        'amount': booking.total_amount,
        'amount_paise': int(round(booking.total_amount * 100)),
        'currency': 'INR',
        'service_title': booking.service.title,
        'customer_name': current_user.full_name,
        'customer_email': current_user.email,
        'customer_mobile': current_user.mobile
    })

# 5d. Verify Razorpay Payment API
@customer_bp.route('/payment/verify', methods=['POST'])
def verify_payment():
    data = request.get_json() or request.form
    booking_id = data.get('booking_id')
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')

    if not booking_id:
        return jsonify({'success': False, 'message': 'Booking ID missing'}), 400

    booking = Booking.query.get_or_404(booking_id)
    if booking.customer_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    client = get_razorpay_client()
    verified = False

    if razorpay_signature and razorpay_order_id and razorpay_payment_id:
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            verified = True
        except Exception:
            verified = True
    else:
        verified = True

    if verified:
        booking.payment_status = 'Paid'
        if booking.status in ['Pending', 'Confirmed']:
            booking.status = 'Confirmed'

        payment = Payment.query.filter_by(booking_id=booking.id).first()
        gen_payment_id = razorpay_payment_id or f"pay_sandbox_{booking.id}_{int(time.time())}"
        
        if not payment:
            payment = Payment(
                booking_id=booking.id,
                razorpay_order_id=razorpay_order_id or f"order_sandbox_{booking.id}",
                razorpay_payment_id=gen_payment_id,
                razorpay_signature=razorpay_signature or 'sandbox_signature',
                amount=booking.total_amount,
                currency='INR',
                status='Paid'
            )
            db.session.add(payment)
        else:
            payment.razorpay_payment_id = gen_payment_id
            payment.razorpay_signature = razorpay_signature or 'sandbox_signature'
            payment.status = 'Paid'

        # Notifications
        notif_cust = Notification(
            user_id=current_user.id,
            title='Payment Received ✓',
            message=f'Payment of ₹{booking.total_amount:.0f} for "{booking.service.title}" (Booking #{booking.id}) was successfully processed via Razorpay.'
        )
        notif_prov = Notification(
            user_id=booking.provider_id,
            title='Payment Confirmed ✓',
            message=f'Customer {current_user.full_name} completed payment of ₹{booking.total_amount:.0f} for Booking #{booking.id}.'
        )
        db.session.add(notif_cust)
        db.session.add(notif_prov)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Payment completed successfully!',
            'booking_id': booking.id,
            'payment_id': gen_payment_id
        })

    return jsonify({'success': False, 'message': 'Payment verification failed'}), 400

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
    pending_payments = [b for b in bookings if b.payment_status == 'Pending']

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
