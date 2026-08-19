from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from database import db, User, ProviderProfile, Category, Service, Booking, ContactMessage, Notification

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
def check_admin_role():
    if current_user.role != 'admin':
        flash('Access restricted to Platform Administrators.', 'danger')
        return redirect(url_for('public.home'))

# 1. Admin Dashboard Overview
@admin_bp.route('/dashboard')
def dashboard():
    pending_providers = ProviderProfile.query.join(User).filter(User.status == 'Pending').all()
    approved_providers = ProviderProfile.query.join(User).filter(User.status == 'Approved').all()
    customers = User.query.filter_by(role='customer').all()
    categories = Category.query.all()
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    recent_bookings = bookings[:5]
    recent_contact_messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(5).all()

    total_platform_revenue = sum(b.total_amount for b in bookings if b.status == 'Completed')

    stats = {
        'total_users': User.query.count(),
        'pending_approvals': len(pending_providers),
        'approved_providers': len(approved_providers),
        'total_customers': len(customers),
        'total_bookings': len(bookings),
        'platform_revenue': total_platform_revenue,
        'total_categories': len(categories)
    }

    return render_template('admin/dashboard.html',
                           pending_providers=pending_providers,
                           recent_bookings=recent_bookings,
                           recent_contact_messages=recent_contact_messages,
                           stats=stats,
                           active_page='dashboard')

# 2. Provider Verification Queue Page
@admin_bp.route('/providers')
def providers():
    status_filter = request.args.get('status', 'Pending')
    
    query = ProviderProfile.query.join(User)
    if status_filter != 'All':
        query = query.filter(User.status == status_filter)
        
    providers_list = query.order_by(User.created_at.desc()).all()

    return render_template('admin/providers.html', 
                           providers=providers_list, 
                           current_filter=status_filter, 
                           active_page='providers')

# 3. Approve Provider
@admin_bp.route('/provider/approve/<int:user_id>', methods=['POST'])
def approve_provider(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'provider':
        user.status = 'Approved'
        
        # Notify Provider
        notif = Notification(
            user_id=user.id,
            title='Account Verification Approved!',
            message='Congratulations! Your provider account has been approved by Admin. You can now access your Provider Dashboard and manage service listings.'
        )
        db.session.add(notif)
        db.session.commit()
        
        flash(f'Provider "{user.full_name}" has been approved successfully!', 'success')

    redirect_to = request.referrer or url_for('admin.providers')
    return redirect(redirect_to)

# 4. Reject Provider
@admin_bp.route('/provider/reject/<int:user_id>', methods=['POST'])
def reject_provider(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'provider':
        user.status = 'Rejected'
        
        # Notify Provider
        notif = Notification(
            user_id=user.id,
            title='Account Application Status',
            message='Your provider application was not approved by administration.'
        )
        db.session.add(notif)
        db.session.commit()
        
        flash(f'Provider application for "{user.full_name}" has been rejected.', 'warning')

    redirect_to = request.referrer or url_for('admin.providers')
    return redirect(redirect_to)

# 5. User Management Page
@admin_bp.route('/users')
def users():
    role_filter = request.args.get('role', 'All')
    
    query = User.query
    if role_filter != 'All':
        query = query.filter_by(role=role_filter)
        
    users_list = query.order_by(User.created_at.desc()).all()

    return render_template('admin/users.html', 
                           users=users_list, 
                           current_filter=role_filter, 
                           active_page='users')

# 6. Toggle User Account Status (Suspend / Activate)
@admin_bp.route('/user/toggle-status/<int:user_id>', methods=['POST'])
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot suspend your own admin account.', 'danger')
        return redirect(url_for('admin.users'))

    if user.status == 'Approved':
        user.status = 'Suspended'
        flash(f'User "{user.full_name}" account has been suspended.', 'warning')
    else:
        user.status = 'Approved'
        flash(f'User "{user.full_name}" account has been activated.', 'success')

    db.session.commit()
    return redirect(url_for('admin.users'))

# 7. Service Categories CRUD Page
@admin_bp.route('/categories')
def categories():
    categories_list = Category.query.all()
    return render_template('admin/categories.html', categories=categories_list, active_page='categories')

# 8. Add Service Category
@admin_bp.route('/category/add', methods=['POST'])
def add_category():
    name = request.form.get('name', '').strip()
    slug = request.form.get('slug', '').strip().lower().replace(' ', '-')
    description = request.form.get('description', '').strip()
    icon = request.form.get('icon', 'fa-tools').strip()

    if not name or not slug:
        flash('Category name and slug are required.', 'danger')
        return redirect(url_for('admin.categories'))

    existing_cat = Category.query.filter((Category.name == name) | (Category.slug == slug)).first()
    if existing_cat:
        flash('A category with this name or slug already exists.', 'warning')
        return redirect(url_for('admin.categories'))

    category = Category(name=name, slug=slug, description=description, icon=icon)
    db.session.add(category)
    db.session.commit()

    flash(f'Service Category "{name}" created successfully.', 'success')
    return redirect(url_for('admin.categories'))

# 9. Edit Service Category
@admin_bp.route('/category/edit/<int:category_id>', methods=['POST'])
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    name = request.form.get('name', '').strip()
    slug = request.form.get('slug', '').strip().lower().replace(' ', '-')
    description = request.form.get('description', '').strip()
    icon = request.form.get('icon', category.icon).strip()

    if not name or not slug:
        flash('Category name and slug are required.', 'danger')
        return redirect(url_for('admin.categories'))

    category.name = name
    category.slug = slug
    category.description = description
    category.icon = icon
    db.session.commit()

    flash(f'Service Category "{name}" updated successfully.', 'success')
    return redirect(url_for('admin.categories'))

# 10. Delete Service Category
@admin_bp.route('/category/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash(f'Category "{category.name}" deleted successfully.', 'info')
    return redirect(url_for('admin.categories'))

# 11. Platform Bookings Log & Revenue Reports
@admin_bp.route('/bookings')
def bookings():
    status_filter = request.args.get('status', 'All')
    
    query = Booking.query
    if status_filter != 'All':
        query = query.filter_by(status=status_filter)
        
    bookings_list = query.order_by(Booking.created_at.desc()).all()
    total_revenue = sum(b.total_amount for b in bookings_list if b.status == 'Completed')

    return render_template('admin/bookings.html', 
                           bookings=bookings_list, 
                           current_filter=status_filter, 
                           total_revenue=total_revenue,
                           active_page='bookings')

# 12. Contact Messages & Inquiries
@admin_bp.route('/contact-messages')
def contact_messages():
    messages_list = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/contact_messages.html', contact_messages=messages_list, active_page='contact_messages')
