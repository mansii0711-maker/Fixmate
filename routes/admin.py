from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database import db, User, ProviderProfile, CustomerProfile, Category, Service, Booking, Payment, ContactMessage, Notification

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
def check_admin_role():
    if current_user.role != 'admin':
        flash('Access restricted to Platform Administrators.', 'danger')
        return redirect(url_for('public.home'))

@admin_bp.route('/dashboard')
def dashboard():
    pending_providers = ProviderProfile.query.join(User).filter(User.status == 'Pending').all()
    approved_providers = ProviderProfile.query.join(User).filter(User.status == 'Approved').all()
    all_providers = ProviderProfile.query.join(User).all()
    customers = User.query.filter_by(role='customer').all()
    categories = Category.query.all()
    services = Service.query.order_by(Service.created_at.desc()).all()
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    contact_messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()

    total_platform_revenue = sum(b.total_amount for b in bookings if b.payment_status == 'Paid' or b.status == 'Completed')
    online_paid_bookings = [b for b in bookings if b.payment_method == 'Razorpay' and b.payment_status == 'Paid']
    cod_bookings = [b for b in bookings if b.payment_method == 'COD']
    pending_payments = [b for b in bookings if b.payment_status == 'Pending']
    failed_payments = [b for b in bookings if b.payment_status == 'Failed']

    stats = {
        'total_users': User.query.count(),
        'pending_approvals': len(pending_providers),
        'approved_providers': len(approved_providers),
        'all_providers_count': len(all_providers),
        'total_customers': len(customers),
        'total_services': len(services),
        'total_bookings': len(bookings),
        'platform_revenue': total_platform_revenue,
        'online_payments_count': len(online_paid_bookings),
        'online_payments_sum': sum(b.total_amount for b in online_paid_bookings),
        'cod_bookings_count': len(cod_bookings),
        'cod_bookings_sum': sum(b.total_amount for b in cod_bookings),
        'pending_payments_count': len(pending_payments),
        'failed_payments_count': len(failed_payments)
    }

    return render_template('admin/dashboard.html',
                           pending_providers=pending_providers,
                           approved_providers=approved_providers,
                           all_providers=all_providers,
                           customers=customers,
                           categories=categories,
                           services=services,
                           bookings=bookings,
                           online_paid_bookings=online_paid_bookings,
                           cod_bookings=cod_bookings,
                           contact_messages=contact_messages,
                           stats=stats)

# Provider Approval / Rejection / Management
@admin_bp.route('/provider/approve/<int:user_id>', methods=['POST'])
def approve_provider(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'provider':
        user.status = 'Approved'
        notif = Notification(
            user_id=user.id,
            title='Provider Application Approved ✓',
            message='Congratulations! Your provider profile has been approved by Admin. You can now post services and accept booking requests.'
        )
        db.session.add(notif)
        db.session.commit()
        flash(f'Provider "{user.full_name}" has been approved successfully!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/provider/reject/<int:user_id>', methods=['POST'])
def reject_provider(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'provider':
        user.status = 'Rejected'
        notif = Notification(
            user_id=user.id,
            title='Provider Application Status Update',
            message='Your provider verification request was not approved. Please review your credentials and re-apply.'
        )
        db.session.add(notif)
        db.session.commit()
        flash(f'Provider application for "{user.full_name}" has been rejected.', 'warning')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/provider/toggle-status/<int:user_id>', methods=['POST'])
def toggle_provider_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'provider':
        user.status = 'Suspended' if user.status == 'Approved' else 'Approved'
        db.session.commit()
        flash(f'Provider "{user.full_name}" account status updated to {user.status}.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/provider/delete/<int:user_id>', methods=['POST'])
def delete_provider(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'provider':
        active_bookings = Booking.query.filter_by(provider_id=user.id).filter(Booking.status.in_(['Pending', 'Confirmed'])).first()
        if active_bookings:
            flash(f'Cannot delete provider "{user.full_name}" because they have active ongoing bookings.', 'danger')
            return redirect(url_for('admin.dashboard'))

        db.session.delete(user)
        db.session.commit()
        flash(f'Provider "{user.full_name}" deleted successfully.', 'info')
    return redirect(url_for('admin.dashboard'))

# Customer Management
@admin_bp.route('/customer/toggle-status/<int:user_id>', methods=['POST'])
def toggle_customer_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'customer':
        user.status = 'Suspended' if user.status == 'Approved' else 'Approved'
        db.session.commit()
        flash(f'Customer "{user.full_name}" account status updated to {user.status}.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/customer/delete/<int:user_id>', methods=['POST'])
def delete_customer(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'customer':
        active_bookings = Booking.query.filter_by(customer_id=user.id).filter(Booking.status.in_(['Pending', 'Confirmed'])).first()
        if active_bookings:
            flash(f'Cannot delete customer "{user.full_name}" because they have active ongoing bookings.', 'danger')
            return redirect(url_for('admin.dashboard'))

        db.session.delete(user)
        db.session.commit()
        flash(f'Customer "{user.full_name}" deleted successfully.', 'info')
    return redirect(url_for('admin.dashboard'))

# Service Management
@admin_bp.route('/service/toggle-status/<int:service_id>', methods=['POST'])
def toggle_service_status(service_id):
    service = Service.query.get_or_404(service_id)
    service.is_active = not service.is_active
    db.session.commit()
    status_str = 'Activated' if service.is_active else 'Deactivated'
    flash(f'Service "{service.title}" has been {status_str}.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/service/delete/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    active_bookings = Booking.query.filter_by(service_id=service.id).filter(Booking.status.in_(['Pending', 'Confirmed'])).first()
    if active_bookings:
        flash(f'Cannot delete service "{service.title}" because active bookings rely on it.', 'danger')
        return redirect(url_for('admin.dashboard'))

    db.session.delete(service)
    db.session.commit()
    flash(f'Service "{service.title}" deleted successfully.', 'info')
    return redirect(url_for('admin.dashboard'))

# Category Management
@admin_bp.route('/category/add', methods=['POST'])
def add_category():
    name = request.form.get('name', '').strip()
    slug = request.form.get('slug', '').strip().lower().replace(' ', '-')
    description = request.form.get('description', '').strip()
    icon = request.form.get('icon', 'fa-tools').strip()

    if not name or not slug:
        flash('Category name and slug are required.', 'danger')
        return redirect(url_for('admin.dashboard'))

    category = Category(name=name, slug=slug, description=description, icon=icon)
    db.session.add(category)
    db.session.commit()

    flash(f'Service Category "{name}" created successfully.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/category/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    services_count = Service.query.filter_by(category_id=category.id).count()
    if services_count > 0:
        flash(f'Cannot delete category "{category.name}" because {services_count} active service(s) belong to it.', 'danger')
        return redirect(url_for('admin.dashboard'))

    db.session.delete(category)
    db.session.commit()
    flash(f'Category "{category.name}" deleted successfully.', 'info')
    return redirect(url_for('admin.dashboard'))
