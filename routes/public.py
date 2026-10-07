from flask import Blueprint, render_template, request, flash, redirect, url_for
from database import db, Category, Service, ProviderProfile, User, Review, ContactMessage

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def home():
    categories = Category.query.all()
    popular_services = Service.query.filter_by(is_active=True).limit(6).all()
    recent_reviews = Review.query.order_by(Review.created_at.desc()).limit(3).all()
    
    # Calculate key statistics for display
    stats = {
        'verified_providers': ProviderProfile.query.join(User).filter(User.status == 'Approved').count(),
        'completed_bookings': 150, # Dynamic / visual count
        'satisfied_customers': User.query.filter_by(role='customer').count(),
        'service_categories': len(categories)
    }
    
    return render_template('home.html', 
                           categories=categories, 
                           popular_services=popular_services, 
                           recent_reviews=recent_reviews,
                           stats=stats)

@public_bp.route('/services')
def services():
    category_slug = request.args.get('category', '')
    search_query = request.args.get('q', '').strip()
    area_query = request.args.get('area', '').strip()
    max_price = request.args.get('max_price', '')
    min_rating = request.args.get('min_rating', '')
    
    query = Service.query.join(ProviderProfile).join(User).filter(User.status == 'Approved', Service.is_active == True)
    
    if category_slug:
        cat = Category.query.filter_by(slug=category_slug).first()
        if cat:
            query = query.filter(Service.category_id == cat.id)
            
    if search_query:
        query = query.filter(
            (Service.title.ilike(f'%{search_query}%')) | 
            (Service.description.ilike(f'%{search_query}%'))
        )

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
    
    return render_template('services.html', 
                           services=services_list, 
                           categories=categories, 
                           selected_category=category_slug,
                           search_query=search_query,
                           area_query=area_query,
                           max_price=max_price,
                           min_rating=min_rating)

@public_bp.route('/services/<int:service_id>')
def service_detail(service_id):
    service = Service.query.get_or_404(service_id)
    provider_user = User.query.get(service.provider.user_id)
    reviews = Review.query.filter_by(provider_id=provider_user.id).order_by(Review.created_at.desc()).all()
    
    return render_template('service_detail.html', service=service, provider=provider_user, reviews=reviews)

@public_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        if not name or not email or not message:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('public.contact'))

        contact_msg = ContactMessage(
            name=name,
            email=email,
            subject=subject or 'General Inquiry',
            message=message
        )
        db.session.add(contact_msg)
        db.session.commit()

        flash('Thank you for contacting FixMate! Our support team will get back to you shortly.', 'success')
        return redirect(url_for('public.contact'))

    return render_template('contact.html')

@public_bp.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')
