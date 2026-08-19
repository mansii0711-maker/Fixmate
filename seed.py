from app import create_app
from database import db, User, CustomerProfile, ProviderProfile, Category, Service, Booking, Review, ContactMessage
from werkzeug.security import generate_password_hash

app = create_app()

def seed_database():
    with app.app_context():
        # Drop all tables and recreate clean structure
        db.drop_all()
        db.create_all()
        
        print("Database tables created cleanly.")

        # 1. Seed Categories
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
            c = Category(name=cat['name'], slug=cat['slug'], description=cat['description'], icon=cat['icon'])
            db.session.add(c)
            cat_objs[cat['slug']] = c

        db.session.commit()
        print("Categories seeded.")

        # 2. Seed Admin User
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

        # 3. Seed Sample Customers
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

        # Common sample operating areas covered by providers
        sample_areas = 'Dadar, Bandra, Andheri, Powai, Thane'

        # 4. Seed Sample Approved Providers for ALL 6 Categories
        # Provider 1: Electrician
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
            operating_area=sample_areas,
            verification_doc='rajesh_electrical_cert.pdf',
            rating=4.9,
            total_reviews=28
        )
        db.session.add(pp1)

        # Provider 2: Plumber
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
            operating_area=sample_areas,
            verification_doc='vikram_license.pdf',
            rating=4.8,
            total_reviews=19
        )
        db.session.add(pp2)

        # Provider 3: Carpenter
        p3 = User(
            full_name='Ramesh Sutar',
            email='ramesh@carpentryworks.com',
            mobile='9822114455',
            address='Timber Market, Bandra West, Mumbai',
            role='provider',
            status='Approved'
        )
        p3.set_password('ramesh123')
        db.session.add(p3)
        db.session.flush()

        pp3 = ProviderProfile(
            user_id=p3.id,
            experience=10,
            qualification='Master Craftsman Woodworking Certification',
            category_id=cat_objs['carpenter'].id,
            operating_area=sample_areas,
            verification_doc='ramesh_carpenter_cert.pdf',
            rating=4.9,
            total_reviews=25
        )
        db.session.add(pp3)

        # Provider 4: Cleaning Expert
        p4 = User(
            full_name='Sunita Verma',
            email='sunita@shinecleaning.com',
            mobile='9765432109',
            address='Block B, Green View Society, Powai, Mumbai',
            role='provider',
            status='Approved'
        )
        p4.set_password('sunita123')
        db.session.add(p4)
        db.session.flush()

        pp4 = ProviderProfile(
            user_id=p4.id,
            experience=5,
            qualification='Professional Sanitation & Hygiene Certification',
            category_id=cat_objs['cleaning'].id,
            operating_area=sample_areas,
            verification_doc='sunita_id_proof.pdf',
            rating=5.0,
            total_reviews=14
        )
        db.session.add(pp4)

        # Provider 5: Appliance Repair
        p5 = User(
            full_name='Amit Roy',
            email='amit@coolfix.com',
            mobile='9834567812',
            address='Sector 17, Vashi, Navi Mumbai',
            role='provider',
            status='Approved'
        )
        p5.set_password('amit123')
        db.session.add(p5)
        db.session.flush()

        pp5 = ProviderProfile(
            user_id=p5.id,
            experience=7,
            qualification='HVAC & Refrigeration Technician Certification',
            category_id=cat_objs['appliance-repair'].id,
            operating_area=sample_areas,
            verification_doc='amit_hvac.pdf',
            rating=4.7,
            total_reviews=22
        )
        db.session.add(pp5)

        # Provider 6: Home Tutor
        p6 = User(
            full_name='Ananya Roy',
            email='ananya@tutorhub.com',
            mobile='9933445566',
            address='22 Academic Chambers, Andheri East, Mumbai',
            role='provider',
            status='Approved'
        )
        p6.set_password('ananya123')
        db.session.add(p6)
        db.session.flush()

        pp6 = ProviderProfile(
            user_id=p6.id,
            experience=6,
            qualification='M.Sc. Mathematics & B.Ed.',
            category_id=cat_objs['home-tutor'].id,
            operating_area=sample_areas,
            verification_doc='ananya_degree_cert.pdf',
            rating=5.0,
            total_reviews=18
        )
        db.session.add(pp6)

        # 5. Seed Pending Provider (for Admin Approval Testing)
        p_pending = User(
            full_name='Deepak Sharma',
            email='deepak@tutor.com',
            mobile='9911223344',
            address='22 College Road, Borivali East, Mumbai',
            role='provider',
            status='Pending'
        )
        p_pending.set_password('deepak123')
        db.session.add(p_pending)
        db.session.flush()

        pp_pending = ProviderProfile(
            user_id=p_pending.id,
            experience=4,
            qualification='M.Sc. Mathematics & Physics',
            category_id=cat_objs['home-tutor'].id,
            operating_area='Borivali, Kandivali, Malad',
            verification_doc='deepak_degree_certificate.pdf',
            rating=5.0,
            total_reviews=0
        )
        db.session.add(pp_pending)

        db.session.commit()
        print("Providers seeded for ALL categories.")

        # 6. Seed Services for All Categories
        services_data = [
            # Electrician Services
            {
                'provider_id': pp1.id,
                'category_id': cat_objs['electrician'].id,
                'title': 'Complete Home Electrical Inspection & Wiring Repair',
                'description': 'Thorough inspection of circuit breakers, main switchboards, exposed wiring, and short-circuit fault troubleshooting.',
                'price': 499.0,
                'price_type': 'Per Visit'
            },
            {
                'provider_id': pp1.id,
                'category_id': cat_objs['electrician'].id,
                'title': 'Ceiling Fan & Decorative Light Fitting',
                'description': 'Safe installation of ceiling fans, chandeliers, wall sconces, and LED strip lights.',
                'price': 299.0,
                'price_type': 'Fixed'
            },
            # Plumber Services
            {
                'provider_id': pp2.id,
                'category_id': cat_objs['plumber'].id,
                'title': 'Emergency Leak Repair & Tap Replacement',
                'description': 'Quick fixing of leaking pipes, damaged faucets, flush valves, and kitchen sink blockages.',
                'price': 350.0,
                'price_type': 'Fixed'
            },
            {
                'provider_id': pp2.id,
                'category_id': cat_objs['plumber'].id,
                'title': 'Water Heater (Geyser) Installation & Servicing',
                'description': 'Installation, de-scaling, and thermostat repair for storage and instant geysers.',
                'price': 599.0,
                'price_type': 'Fixed'
            },
            # Carpenter Services
            {
                'provider_id': pp3.id,
                'category_id': cat_objs['carpenter'].id,
                'title': 'Furniture Repair & Custom Woodwork Fitting',
                'description': 'Expert repair for wooden beds, dining tables, wardrobes, door hinges, and custom woodwork assembly.',
                'price': 450.0,
                'price_type': 'Per Visit'
            },
            {
                'provider_id': pp3.id,
                'category_id': cat_objs['carpenter'].id,
                'title': 'Door & Window Lock Installation & Repair',
                'description': 'Fitting high-security door locks, latch alignment, handle replacement, and window frame fixing.',
                'price': 299.0,
                'price_type': 'Fixed'
            },
            # Cleaning Services
            {
                'provider_id': pp4.id,
                'category_id': cat_objs['cleaning'].id,
                'title': 'Full Home Deep Sanitization & Deep Cleaning (2 BHK / 3 BHK)',
                'description': 'Deep scrub of floors, kitchen tiles, balcony, windows, and bathroom sanitization using eco-friendly agents.',
                'price': 2499.0,
                'price_type': 'Fixed'
            },
            {
                'provider_id': pp4.id,
                'category_id': cat_objs['cleaning'].id,
                'title': 'Fabric Sofa & Carpet Shampooing',
                'description': 'Injection-extraction deep shampooing for stain removal, dust mite elimination, and fresh fragrance.',
                'price': 799.0,
                'price_type': 'Fixed'
            },
            # Appliance Repair
            {
                'provider_id': pp5.id,
                'category_id': cat_objs['appliance-repair'].id,
                'title': 'Split & Window AC Servicing + Gas Top-up',
                'description': 'High-pressure jet wash cleaning, filter sanitization, refrigerant leak check, and gas refill.',
                'price': 899.0,
                'price_type': 'Per Visit'
            },
            # Home Tutor Services
            {
                'provider_id': pp6.id,
                'category_id': cat_objs['home-tutor'].id,
                'title': 'Class 8-10 Mathematics & Physics Home Tutoring',
                'description': 'Personalized 1-on-1 home academic tutoring covering algebra, geometry, physics concepts, and exam prep.',
                'price': 600.0,
                'price_type': 'Per Hour'
            },
            {
                'provider_id': pp6.id,
                'category_id': cat_objs['home-tutor'].id,
                'title': 'Basic & Advanced Python Programming Tutoring',
                'description': 'Interactive coding lessons covering Python syntax, data structures, web development, and problem solving.',
                'price': 750.0,
                'price_type': 'Per Hour'
            }
        ]

        service_objs = []
        for s in services_data:
            serv = Service(
                provider_id=s['provider_id'],
                category_id=s['category_id'],
                title=s['title'],
                description=s['description'],
                price=s['price'],
                price_type=s['price_type'],
                is_active=True
            )
            db.session.add(serv)
            service_objs.append(serv)

        db.session.commit()
        print("Services seeded for ALL categories.")

        # 7. Seed Sample Bookings
        b1 = Booking(
            customer_id=customer1.id,
            provider_id=p1.id,
            service_id=service_objs[0].id,
            booking_date='2026-07-28',
            time_slot='10:00 AM - 12:00 PM',
            status='Confirmed',
            payment_status='Paid',
            total_amount=499.0,
            address='Flat 302, Sunrise Heights, Andheri West, Mumbai',
            notes='Main hall fan switch spark issue.'
        )
        db.session.add(b1)

        b2 = Booking(
            customer_id=customer2.id,
            provider_id=p4.id,
            service_id=service_objs[6].id,
            booking_date='2026-07-27',
            time_slot='02:00 PM - 04:00 PM',
            status='Completed',
            payment_status='Paid',
            total_amount=2499.0,
            address='12 Rose Villa, Bandra West, Mumbai',
            notes='Please bring heavy-duty floor scrubber.'
        )
        db.session.add(b2)
        db.session.flush()

        # 8. Seed Customer Review
        rev = Review(
            booking_id=b2.id,
            customer_id=customer2.id,
            provider_id=p4.id,
            rating=5,
            comment='Sunita and her team did an absolutely marvelous job cleaning our home! Extremely punctual and professional.'
        )
        db.session.add(rev)

        # 9. Seed Contact Message
        cm = ContactMessage(
            name='Karan Mehta',
            email='karan@gmail.com',
            subject='Inquiry about Provider Registration in Navi Mumbai',
            message='Hello FixMate team, I run an appliance service center in Vashi and would like to register 5 technicians.'
        )
        db.session.add(cm)

        db.session.commit()
        print("Initial database seed completed successfully!")

if __name__ == '__main__':
    seed_database()
