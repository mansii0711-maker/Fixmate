import os
import re
import random
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from database import db, User, CustomerProfile, ProviderProfile, Category, Notification

auth_bp = Blueprint('auth', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user)

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'warning')
            return render_template('login.html')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if user.role == 'provider' and user.status == 'Pending':
                flash('Your provider account is currently pending Admin verification. You will be able to access your dashboard once approved.', 'info')
                return render_template('login.html')
            
            if user.status == 'Rejected':
                flash('Your account application was not approved by administration.', 'danger')
                return render_template('login.html')

            if user.status == 'Suspended':
                flash('Your account has been suspended by Administration. Please contact support.', 'danger')
                return render_template('login.html')

            login_user(user)
            
            # Feature 3: Login Welcome Notification
            login_time_str = datetime.now().strftime('%b %d, %Y at %I:%M %p')
            login_notif = Notification(
                user_id=user.id,
                title='Account Login Notification',
                message=f'You successfully logged in to your FixMate account on {login_time_str}.'
            )
            db.session.add(login_notif)
            db.session.commit()

            flash(f'Welcome back, {user.full_name}! Login notification sent to your dashboard.', 'success')
            return redirect_role_dashboard(user)
        else:
            flash('Invalid email address or password. Please check your credentials.', 'danger')

    return render_template('login.html')

def send_real_email_otp(to_email, otp_code):
    mail_user = current_app.config.get('MAIL_USERNAME') or os.environ.get('MAIL_USERNAME', '')
    mail_pass = current_app.config.get('MAIL_PASSWORD') or os.environ.get('MAIL_PASSWORD', '')
    smtp_server = current_app.config.get('MAIL_SERVER') or os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    smtp_port = int(current_app.config.get('MAIL_PORT') or os.environ.get('MAIL_PORT', 587))

    if mail_user and mail_pass:
        try:
            msg = MIMEMultipart()
            msg['From'] = f"FixMate Security <{mail_user}>"
            msg['To'] = to_email
            msg['Subject'] = "FixMate Password Reset OTP"

            body = f"""Hello,

Your FixMate password reset OTP is {otp_code}. This OTP is valid for 10 minutes. Do not share it with anyone.

Best regards,
FixMate Security Team"""
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(mail_user, mail_pass)
            server.sendmail(mail_user, to_email, msg.as_string())
            server.quit()
            return True, None
        except Exception as e:
            return False, str(e)
    return False, "SMTP credentials missing. Please set MAIL_USERNAME and MAIL_PASSWORD (Gmail App Password) in config.py or environment."

# Feature 4: Forgot Password Request (Sends OTP to Registered Gmail Address)
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user)

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()

        if not identifier:
            flash('Please enter your registered Gmail address.', 'warning')
            return render_template('forgot_password.html')

        user = User.query.filter_by(email=identifier.lower()).first()

        if not user:
            flash('No FixMate account found matching this Gmail address. Please enter a valid registered email.', 'danger')
            return render_template('forgot_password.html')

        # Generate secure 6-digit Reset OTP & 10-minute expiry
        otp_code = str(random.randint(100000, 999999))
        session['reset_email'] = user.email
        session['reset_otp'] = otp_code
        session['reset_otp_expiry'] = time.time() + 600  # Valid for 10 minutes

        # Dispatch email via real SMTP if credentials configured
        sent, err_msg = send_real_email_otp(user.email, otp_code)

        if sent:
            flash(f'Password reset OTP has been sent to your registered Gmail address ({user.email}). Please check your inbox.', 'success')
        else:
            flash(f'OTP generated for {user.email}. ({err_msg})', 'info')

        return redirect(url_for('auth.reset_password'))

    return render_template('forgot_password.html')

# Feature 4: Reset Password with 10-Minute Email OTP Verification
@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user)

    reset_email = session.get('reset_email')
    correct_otp = session.get('reset_otp')
    otp_expiry = session.get('reset_otp_expiry', 0)

    if not reset_email or not correct_otp:
        flash('Session expired or invalid reset request. Please request a new OTP.', 'warning')
        return redirect(url_for('auth.forgot_password'))

    if time.time() > otp_expiry:
        session.pop('reset_email', None)
        session.pop('reset_otp', None)
        session.pop('reset_otp_expiry', None)
        flash('The 6-digit OTP code has expired (valid for 10 minutes). Please request a new OTP.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        input_otp = request.form.get('otp', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if input_otp != correct_otp:
            flash('Invalid OTP code. Please enter the 6-digit code sent to your registered email.', 'danger')
            return render_template('reset_password.html', email=reset_email)

        if len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'danger')
            return render_template('reset_password.html', email=reset_email)

        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html', email=reset_email)

        user = User.query.filter_by(email=reset_email).first()
        if user:
            user.set_password(new_password)
            
            # Send Notification for password reset
            reset_notif = Notification(
                user_id=user.id,
                title='Password Reset Successful',
                message='Your FixMate account password was updated successfully.'
            )
            db.session.add(reset_notif)
            db.session.commit()

            # Clear session keys
            session.pop('reset_email', None)
            session.pop('reset_otp', None)
            session.pop('reset_otp_expiry', None)

            flash('Password reset successfully! You can now log in with your new password.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('reset_password.html', email=reset_email)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user)

    categories = Category.query.all()

    if request.method == 'POST':
        role = request.form.get('role', 'customer')
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        mobile = request.form.get('mobile', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Standard Field Validations
        if not full_name or not email or not mobile or not address or not password:
            flash('Please fill in all required fields.', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        # 1. Full Name Validation (Letters and spaces, 3-50 chars)
        if not re.match(r'^[a-zA-Z\s]{3,50}$', full_name):
            flash('Full Name must contain only alphabetic characters and spaces (3 to 50 characters).', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        # 2. Standard Email Format Regex Validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('Please enter a valid standard email address (e.g. name@domain.com).', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        # 3. Standard Indian Mobile Number Format (TRAI 10-digit starting with 6, 7, 8, or 9)
        clean_mobile = re.sub(r'[\s\-\(\)\+]', '', mobile)
        if clean_mobile.startswith('91') and len(clean_mobile) == 12:
            clean_mobile = clean_mobile[2:]
        elif clean_mobile.startswith('0') and len(clean_mobile) == 11:
            clean_mobile = clean_mobile[1:]

        if not re.match(r'^[6-9]\d{9}$', clean_mobile):
            flash('Mobile number must be a valid 10-digit Indian phone number starting with 6, 7, 8, or 9.', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        mobile = clean_mobile

        # 4. Detailed Address Length Check (Minimum 10 chars)
        if len(address) < 10:
            flash('Please provide a complete address (minimum 10 characters long).', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        # 5. Password Complexity & Match
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        if password != confirm_password:
            flash('Passwords do not match. Please re-enter passwords carefully.', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email address already exists. Please login instead.', 'warning')
            return render_template('register.html', categories=categories, active_tab=role)

        if role == 'customer':
            new_user = User(
                full_name=full_name,
                email=email,
                mobile=mobile,
                address=address,
                role='customer',
                status='Approved'
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()

            cp = CustomerProfile(user_id=new_user.id)
            db.session.add(cp)
            db.session.commit()

            flash('Customer registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))

        elif role == 'provider':
            experience = request.form.get('experience', 0)
            qualification = request.form.get('qualification', '').strip()
            category_id = request.form.get('category_id')
            operating_area = request.form.get('operating_area', '').strip()

            if not qualification or not category_id or not operating_area:
                flash('Please fill in all provider specific fields (qualification, category, operating area).', 'danger')
                return render_template('register.html', categories=categories, active_tab=role)

            if len(qualification) < 3 or len(operating_area) < 3:
                flash('Qualification and Operating Area must be at least 3 characters long.', 'danger')
                return render_template('register.html', categories=categories, active_tab=role)

            # Mandatory File Upload Check for Providers
            if 'verification_doc' not in request.files or request.files['verification_doc'].filename == '':
                flash('Provider verification document (ID proof/certificate) is required for account approval.', 'danger')
                return render_template('register.html', categories=categories, active_tab=role)

            file = request.files['verification_doc']
            if not allowed_file(file.filename):
                flash('Invalid verification document format. Allowed extensions: PDF, PNG, JPG, JPEG, DOC, DOCX.', 'danger')
                return render_template('register.html', categories=categories, active_tab=role)

            sec_filename = secure_filename(file.filename)
            filename = f"provider_{email.split('@')[0]}_{sec_filename}"
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)

            new_user = User(
                full_name=full_name,
                email=email,
                mobile=mobile,
                address=address,
                role='provider',
                status='Pending'  # Provider remains Pending until approved by Admin
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()

            pp = ProviderProfile(
                user_id=new_user.id,
                experience=int(experience) if str(experience).isdigit() else 0,
                qualification=qualification,
                category_id=int(category_id),
                operating_area=operating_area,
                verification_doc=filename,
                rating=5.0,
                total_reviews=0
            )
            db.session.add(pp)
            db.session.commit()

            flash('Provider registration successful! Your profile is pending Admin approval. You will receive access once verified.', 'info')
            return redirect(url_for('auth.login'))

    return render_template('register.html', categories=categories, active_tab='customer')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('public.home'))

def redirect_role_dashboard(user):
    if user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif user.role == 'provider':
        return redirect(url_for('provider.dashboard'))
    else:
        if user.customer_profile and user.customer_profile.default_location:
            session['user_location'] = user.customer_profile.default_location

        if not session.get('user_location'):
            return redirect(url_for('customer.select_location'))
        return redirect(url_for('customer.dashboard'))
