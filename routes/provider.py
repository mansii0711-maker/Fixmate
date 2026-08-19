import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user, logout_user
from werkzeug.utils import secure_filename
from database import db, Booking, Service, ProviderProfile, Category, Review, Notification, User

provider_bp = Blueprint('provider', __name__, url_prefix='/provider')

def allowed_image(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}

@provider_bp.before_request
@login_required
def check_provider_role():
    if current_user.role != 'provider':
        flash('Access restricted to Provider accounts.', 'danger')
        return redirect(url_for('public.home'))

    if current_user.status == 'Suspended':
        logout_user()
        flash('Your account has been suspended by Administration. Access revoked.', 'danger')
        return redirect(url_for('auth.login'))

# 1. Provider Dashboard View
@provider_bp.route('/dashboard')
def dashboard():
    provider_prof = ProviderProfile.query.filter_by(user_id=current_user.id).first()
    if not provider_prof:
        flash('Provider profile not found.', 'danger')
        return redirect(url_for('public.home'))

    bookings = Booking.query.filter_by(provider_id=current_user.id).order_by(Booking.created_at.desc()).all()
    my_services = Service.query.filter_by(provider_id=provider_prof.id).all()

    today_str = datetime.now().strftime('%Y-%m-%d')
    today_bookings_count = len([b for b in bookings if b.booking_date == today_str])
    pending_requests_count = len([b for b in bookings if b.status == 'Pending'])
    completed_jobs_count = len([b for b in bookings if b.status == 'Completed'])

    # Monthly Earnings
    current_month_str = datetime.now().strftime('%Y-%m')
    monthly_earnings = sum(
        b.total_amount for b in bookings 
        if b.status == 'Completed' and (b.created_at.strftime('%Y-%m') == current_month_str or b.booking_date.startswith(current_month_str))
    )

    stats = {
        'today_bookings': today_bookings_count,
        'pending_requests': pending_requests_count,
        'completed_jobs': completed_jobs_count,
        'monthly_earnings': monthly_earnings,
        'rating': provider_prof.rating,
        'total_reviews': provider_prof.total_reviews,
        'active_services': len([s for s in my_services if s.is_active])
    }

    recent_requests = [b for b in bookings if b.status in ['Pending', 'Confirmed']][:5]

    return render_template('provider/dashboard.html', 
                           provider_prof=provider_prof, 
                           bookings=recent_requests, 
                           my_services=my_services, 
                           stats=stats,
                           active_page='dashboard')

# 2. Provider Profile View & Edit
@provider_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    provider_prof = ProviderProfile.query.filter_by(user_id=current_user.id).first_or_404()
    categories = Category.query.all()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        address = request.form.get('address', '').strip()
        experience = request.form.get('experience', 0)
        qualification = request.form.get('qualification', '').strip()
        operating_area = request.form.get('operating_area', '').strip()
        bio = request.form.get('bio', '').strip()
        category_id = request.form.get('category_id')

        if not full_name or not mobile or not address or not qualification or not operating_area:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('provider.profile'))

        current_user.full_name = full_name
        current_user.mobile = mobile
        current_user.address = address

        provider_prof.experience = int(experience) if str(experience).isdigit() else 0
        provider_prof.qualification = qualification
        provider_prof.operating_area = operating_area
        provider_prof.bio = bio
        if category_id:
            provider_prof.category_id = int(category_id)

        # Profile Photo Upload
        if 'photo' in request.files and request.files['photo'].filename != '':
            file = request.files['photo']
            if allowed_image(file.filename):
                sec_filename = secure_filename(file.filename)
                filename = f"avatar_{current_user.id}_{sec_filename}"
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                file.save(upload_path)
                provider_prof.photo = filename

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('provider.profile'))

    return render_template('provider/profile.html', 
                           provider_prof=provider_prof, 
                           categories=categories, 
                           active_page='profile')

# 3. Manage Services Page
@provider_bp.route('/services')
def services():
    provider_prof = ProviderProfile.query.filter_by(user_id=current_user.id).first_or_404()
    my_services = Service.query.filter_by(provider_id=provider_prof.id).order_by(Service.created_at.desc()).all()
    categories = Category.query.all()

    return render_template('provider/services.html', 
                           my_services=my_services, 
                           categories=categories, 
                           provider_prof=provider_prof,
                           active_page='services')

# 4. Add Service
@provider_bp.route('/service/add', methods=['POST'])
def add_service():
    provider_prof = ProviderProfile.query.filter_by(user_id=current_user.id).first_or_404()

    title = request.form.get('title', '').strip()
    category_id = request.form.get('category_id')
    description = request.form.get('description', '').strip()
    price = request.form.get('price', '')
    price_type = request.form.get('price_type', 'Fixed')
    estimated_time = request.form.get('estimated_time', '1-2 Hours').strip()

    if not title or not description or not price or not category_id:
        flash('Please fill in all mandatory service details.', 'danger')
        return redirect(url_for('provider.services'))

    image_filename = None
    if 'image' in request.files and request.files['image'].filename != '':
        file = request.files['image']
        if allowed_image(file.filename):
            sec_filename = secure_filename(file.filename)
            image_filename = f"service_{provider_prof.id}_{sec_filename}"
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)

    service = Service(
        provider_id=provider_prof.id,
        category_id=int(category_id),
        title=title,
        description=description,
        price=float(price),
        price_type=price_type,
        estimated_time=estimated_time,
        image=image_filename,
        is_active=True
    )
    db.session.add(service)
    db.session.commit()

    flash('New service listing created successfully!', 'success')
    return redirect(url_for('provider.services'))

# 5. Edit Service
@provider_bp.route('/service/edit/<int:service_id>', methods=['POST'])
def edit_service(service_id):
    service = Service.query.get_or_404(service_id)
    provider_prof = ProviderProfile.query.filter_by(user_id=current_user.id).first_or_404()

    if service.provider_id != provider_prof.id:
        flash('Unauthorized edit request.', 'danger')
        return redirect(url_for('provider.services'))

    service.title = request.form.get('title', service.title).strip()
    service.category_id = int(request.form.get('category_id', service.category_id))
    service.description = request.form.get('description', service.description).strip()
    service.price = float(request.form.get('price', service.price))
    service.price_type = request.form.get('price_type', service.price_type)
    service.estimated_time = request.form.get('estimated_time', service.estimated_time).strip()

    if 'image' in request.files and request.files['image'].filename != '':
        file = request.files['image']
        if allowed_image(file.filename):
            sec_filename = secure_filename(file.filename)
            image_filename = f"service_{provider_prof.id}_{sec_filename}"
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)
            service.image = image_filename

    db.session.commit()
    flash('Service listing updated successfully!', 'success')
    return redirect(url_for('provider.services'))

# 6. Delete Service
@provider_bp.route('/service/delete/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    provider_prof = ProviderProfile.query.filter_by(user_id=current_user.id).first_or_404()

    if service.provider_id != provider_prof.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('provider.services'))

    db.session.delete(service)
    db.session.commit()
    flash('Service listing deleted successfully.', 'info')
    return redirect(url_for('provider.services'))

# 7. Pause / Activate Service Toggle
@provider_bp.route('/service/toggle-status/<int:service_id>', methods=['POST'])
def toggle_service_status(service_id):
    service = Service.query.get_or_404(service_id)
    provider_prof = ProviderProfile.query.filter_by(user_id=current_user.id).first_or_404()

    if service.provider_id != provider_prof.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('provider.services'))

    service.is_active = not service.is_active
    db.session.commit()

    status_str = 'Activated' if service.is_active else 'Paused'
    flash(f'Service "{service.title}" has been {status_str}.', 'success')
    return redirect(url_for('provider.services'))

# 8. Booking Requests Page
@provider_bp.route('/requests')
def booking_requests():
    status_filter = request.args.get('status', '')
    query = Booking.query.filter_by(provider_id=current_user.id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    bookings = query.order_by(Booking.created_at.desc()).all()

    return render_template('provider/requests.html', 
                           bookings=bookings, 
                           current_filter=status_filter, 
                           active_page='requests')

# 9. Update Booking Status (Accept / Reject / Complete)
@provider_bp.route('/booking/update-status/<int:booking_id>', methods=['POST'])
def update_booking_status(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.provider_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('provider.dashboard'))

    new_status = request.form.get('status')
    if new_status in ['Confirmed', 'Completed', 'Cancelled']:
        booking.status = new_status
        if new_status == 'Completed':
            booking.payment_status = 'Paid'

        # Notify Customer
        notif_msg = f'Your booking for "{booking.service.title}" has been updated to "{new_status}".'
        notif = Notification(user_id=booking.customer_id, title=f'Booking {new_status}', message=notif_msg)
        db.session.add(notif)
        db.session.commit()

        flash(f'Booking status updated to {new_status}. Customer notified.', 'success')

    redirect_to = request.referrer or url_for('provider.dashboard')
    return redirect(redirect_to)

# 10. Schedule View
@provider_bp.route('/schedule')
def schedule():
    confirmed_bookings = Booking.query.filter_by(provider_id=current_user.id, status='Confirmed').order_by(Booking.booking_date.asc()).all()
    return render_template('provider/schedule.html', bookings=confirmed_bookings, active_page='schedule')

# 11. Payments Overview
@provider_bp.route('/payments')
def payments():
    bookings = Booking.query.filter_by(provider_id=current_user.id).order_by(Booking.created_at.desc()).all()
    completed_payments = [b for b in bookings if b.payment_status == 'Paid']
    pending_payments = [b for b in bookings if b.payment_status == 'Pending' and b.status in ['Confirmed', 'Completed']]

    total_earned = sum(b.total_amount for b in completed_payments)

    return render_template('provider/payments.html', 
                           completed_payments=completed_payments, 
                           pending_payments=pending_payments, 
                           total_earned=total_earned,
                           active_page='payments')

# 12. Provider Reviews
@provider_bp.route('/reviews')
def reviews():
    provider_reviews = Review.query.filter_by(provider_id=current_user.id).order_by(Review.created_at.desc()).all()
    provider_prof = ProviderProfile.query.filter_by(user_id=current_user.id).first()

    return render_template('provider/reviews.html', 
                           reviews=provider_reviews, 
                           provider_prof=provider_prof,
                           active_page='reviews')
