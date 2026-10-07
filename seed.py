from app import create_app
from database import db, User, CustomerProfile, ProviderProfile, Category, Service, Booking, Review, ContactMessage, Payment
from werkzeug.security import generate_password_hash

app = create_app()

def seed_database():
    with app.app_context():
        # Ensure all tables exist without dropping existing user data
        db.create_all()
        print("Database schema verified.")

        # 1. Seed Categories if not existing
        categories_data = [
            {'name': 'Electrician', 'slug': 'electrician', 'description': 'Wiring, appliance installation, light fixtures, and electrical repairs.', 'icon': 'fa-bolt'},
            {'name': 'Plumber', 'slug': 'plumber', 'description': 'Pipe repairs, leak fixes, bathroom fitting, and water heater servicing.', 'icon': 'fa-faucet'},
            {'name': 'Carpenter', 'slug': 'carpenter', 'description': 'Furniture repair, custom woodwork, door/window fitting, and assembly.', 'icon': 'fa-hammer'},
            {'name': 'Cleaning', 'slug': 'cleaning', 'description': 'Full home deep cleaning, sofa, carpet, and kitchen sanitization.', 'icon': 'fa-broom'},
            {'name': 'Appliance Repair', 'slug': 'appliance-repair', 'description': 'AC repair, washing machine, refrigerator, and microwave maintenance.', 'icon': 'fa-plug'},
            {'name': 'Home Tutor', 'slug': 'home-tutor', 'description': 'Academic tutoring for Mathematics, Science, English, and Programming.', 'icon': 'fa-graduation-cap'}
        ]

        cat_objs = {}
        for cat in categories_data:
            c = Category.query.filter_by(slug=cat['slug']).first()
            if not c:
                c = Category(name=cat['name'], slug=cat['slug'], description=cat['description'], icon=cat['icon'])
                db.session.add(c)
            cat_objs[cat['slug']] = c

        db.session.commit()

        # 2. Seed Admin User if not existing
        if not User.query.filter_by(email='admin@fixmate.com').first():
            admin = User(
                full_name='System Admin',
                email='admin@fixmate.com',
                mobile='9876543210',
                address='FixMate HQ, Central Tech Park, Sector 5',
                role='admin',
                status='Approved'
            )
            admin.set_password('admin123')
            db.session.add(admin)

        # 3. Seed Sample Customers if not existing
        if not User.query.filter_by(email='customer@fixmate.com').first():
            customer1 = User(
                full_name='Aarav Sharma',
                email='customer@fixmate.com',
                mobile='9812345678',
                address='Flat 302, Sunrise Heights, Andheri West, Mumbai',
                role='customer',
                status='Approved'
            )
            customer1.set_password('customer123')
            db.session.add(customer1)
            db.session.flush()
            cp1 = CustomerProfile(user_id=customer1.id)
            db.session.add(cp1)

        if not User.query.filter_by(email='priya@example.com').first():
            customer2 = User(
                full_name='Priya Patel',
                email='priya@example.com',
                mobile='9823456789',
                address='12 Rose Villa, Bandra West, Mumbai',
                role='customer',
                status='Approved'
            )
            customer2.set_password('priya123')
            db.session.add(customer2)
            db.session.flush()
            cp2 = CustomerProfile(user_id=customer2.id)
            db.session.add(cp2)

        # 4. Seed Sample Approved Providers if not existing
        p1 = User.query.filter_by(email='provider@fixmate.com').first()
        if not p1:
            p1 = User(
                full_name='Rajesh Kumar',
                email='provider@fixmate.com',
                mobile='9988776655',
                address='Shop 4, Spark Electronics Market, Dadar, Mumbai',
                role='provider',
                status='Approved'
            )
            p1.set_password('provider123')
            db.session.add(p1)
            db.session.flush()

            pp1 = ProviderProfile(
                user_id=p1.id,
                experience=8,
                qualification='Diploma in Electrical Engineering (ITI)',
                category_id=cat_objs['electrician'].id,
                operating_area='Dadar, Bandra, Andheri',
                verification_doc='rajesh_electrical_cert.pdf',
                rating=4.9,
                total_reviews=28
            )
            db.session.add(pp1)

        p2 = User.query.filter_by(email='vikram@plumbingsolutions.com').first()
        if not p2:
            p2 = User(
                full_name='Vikram Singh',
                email='vikram@plumbingsolutions.com',
                mobile='9876123450',
                address='15 Waterworks Road, Thane West, Mumbai',
                role='provider',
                status='Approved'
            )
            p2.set_password('vikram123')
            db.session.add(p2)
            db.session.flush()

            pp2 = ProviderProfile(
                user_id=p2.id,
                experience=6,
                qualification='Certified Master Plumber',
                category_id=cat_objs['plumber'].id,
                operating_area='Thane, Mulund, Ghatkopar',
                verification_doc='vikram_license.pdf',
                rating=4.8,
                total_reviews=19
            )
            db.session.add(pp2)

        p3 = User.query.filter_by(email='sunita@shinecleaning.com').first()
        if not p3:
            p3 = User(
                full_name='Sunita Verma',
                email='sunita@shinecleaning.com',
                mobile='9765432109',
                address='Block B, Green View Society, Powai, Mumbai',
                role='provider',
                status='Approved'
            )
            p3.set_password('sunita123')
            db.session.add(p3)
            db.session.flush()

            pp3 = ProviderProfile(
                user_id=p3.id,
                experience=5,
                qualification='Professional Sanitation & Hygiene Certification',
                category_id=cat_objs['cleaning'].id,
                operating_area='Powai, Vikhroli, Kanjurmarg',
                verification_doc='sunita_id_proof.pdf',
                rating=5.0,
                total_reviews=14
            )
            db.session.add(pp3)

        db.session.commit()
        print("Database seed safe check completed successfully! Existing user data preserved.")

if __name__ == '__main__':
    seed_database()
