import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import (Blueprint, render_template, request, flash,
                   redirect, url_for, session, current_app)
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from werkzeug.utils import secure_filename

from database import db, User, CustomerProfile, ProviderProfile, Category, PasswordResetOTP

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

            login_user(user)
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect_role_dashboard(user)
        else:
            flash('Invalid email address or password. Please check your credentials.', 'danger')

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user)

    categories = Category.query.all()

    if request.method == 'POST':
        role = request.form.get('role', 'customer').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        mobile = request.form.get('mobile', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # 1. Role Security Check: Never allow self-registration as 'admin'
        if role not in ['customer', 'provider']:
            flash('Invalid user role selected.', 'danger')
            return render_template('register.html', categories=categories, active_tab='customer')

        # 2. Mandatory Fields Empty Check
        if not full_name or not email or not mobile or not address or not password:
            flash('Please fill in all required fields.', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        # 3. Full Name Validation: Alphabetic & spaces only, 3 to 50 chars
        if not re.match(r'^[a-zA-Z\s]{3,50}$', full_name):
            flash('Please enter a valid name using letters and spaces.', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        # 4. Standard Email Format Regex Validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        # 5. Mobile Number Normalization & 10-digit Indian Mobile Validation (Starts with 6-9)
        clean_mobile = re.sub(r'[\s\-\(\)\+]', '', mobile)
        if clean_mobile.startswith('91') and len(clean_mobile) == 12:
            clean_mobile = clean_mobile[2:]
        elif clean_mobile.startswith('0') and len(clean_mobile) == 11:
            clean_mobile = clean_mobile[1:]

        if not re.match(r'^[6-9]\d{9}$', clean_mobile):
            flash('Enter a valid 10-digit Indian mobile number.', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        mobile = clean_mobile

        # 6. Address Validation (At least 10 chars, valid address chars)
        if len(address) < 10 or not re.match(r'^[a-zA-Z0-9\s\,\.\-\/\#\(\)\:\;]+$', address):
            flash('Please enter a valid address.', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        # 7. Password Complexity Validation (Min 8 chars, 1 uppercase, 1 lowercase, 1 digit)
        if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password):
            flash('Password must contain at least 8 characters, including uppercase, lowercase and a number.', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        if password != confirm_password:
            flash('Passwords do not match. Please re-enter passwords carefully.', 'danger')
            return render_template('register.html', categories=categories, active_tab=role)

        # 8. Duplicate Email Check
        existing_user_email = User.query.filter_by(email=email).first()
        if existing_user_email:
            flash('An account with this email already exists. Please log in or use another email.', 'warning')
            return render_template('register.html', categories=categories, active_tab=role)

        # 9. Duplicate Mobile Check
        existing_user_mobile = User.query.filter_by(mobile=mobile).first()
        if existing_user_mobile:
            flash('An account with this mobile number already exists.', 'warning')
            return render_template('register.html', categories=categories, active_tab=role)

        # 10. Customer Registration
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

        # 11. Provider Registration
        elif role == 'provider':
            experience = request.form.get('experience', '0').strip()
            qualification = request.form.get('qualification', '').strip()
            category_id = request.form.get('category_id')
            operating_area = request.form.get('operating_area', '').strip()

            if not qualification or not category_id or not operating_area:
                flash('Please fill in all provider specific fields (qualification, category, operating area).', 'danger')
                return render_template('register.html', categories=categories, active_tab=role)

            if not str(experience).isdigit() or int(experience) < 0 or int(experience) > 50:
                flash('Please enter a valid experience in years (0 to 50).', 'danger')
                return render_template('register.html', categories=categories, active_tab=role)

            if len(qualification) < 2 or len(operating_area) < 3:
                flash('Please provide valid qualification and operating area details.', 'danger')
                return render_template('register.html', categories=categories, active_tab=role)

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
                status='Pending'
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()

            pp = ProviderProfile(
                user_id=new_user.id,
                experience=int(experience),
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


# ===========================================================================
# FORGOT PASSWORD — Email OTP flow
# Routes: /forgot-password  /forgot-password/verify-otp
#         /forgot-password/resend-otp  /forgot-password/reset
# ===========================================================================

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
OTP_SESSION_KEY   = 'fp_otp_record_id'   # db id of the PasswordResetOTP row
OTP_EMAIL_KEY     = 'fp_email'           # masked email shown on verify page
OTP_VERIFIED_KEY  = 'fp_verified'        # True after OTP is verified
RESEND_AFTER_KEY  = 'fp_resend_after'    # UTC timestamp – cooldown


def _generate_otp():
    """Cryptographically secure 6-digit OTP (000000 – 999999)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _mask_email(email):
    """Return a privacy-masked version: m***@gmail.com"""
    local, domain = email.rsplit('@', 1)
    return local[:2] + '***@' + domain


def _send_otp_email(user, otp):
    """Compose and dispatch the formal OTP email to the user."""
    subject = "FixMate – Password Reset Verification Code"
    html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f5f7; margin: 0; padding: 0; }}
  .wrapper {{ max-width: 560px; margin: 30px auto; }}
  .header {{ background: linear-gradient(135deg, #1e1b4b, #312e81); padding: 30px 36px; border-radius: 12px 12px 0 0; text-align: center; }}
  .header h1 {{ color: #fff; margin: 0; font-size: 1.6rem; letter-spacing: 1px; }}
  .header p {{ color: #c7d2fe; font-size: 0.85rem; margin: 6px 0 0; }}
  .body {{ background: #ffffff; padding: 36px; border-left: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; }}
  .greeting {{ font-size: 1rem; color: #374151; margin-bottom: 16px; }}
  .intro {{ font-size: 0.95rem; color: #6b7280; line-height: 1.6; margin-bottom: 24px; }}
  .otp-box {{ background: #f0f4ff; border: 2px dashed #6366f1; border-radius: 10px; text-align: center; padding: 24px 20px; margin: 0 auto 24px; }}
  .otp-label {{ font-size: 0.78rem; text-transform: uppercase; letter-spacing: 1px; color: #6b7280; margin-bottom: 8px; }}
  .otp-code {{ font-size: 2.6rem; font-weight: 700; letter-spacing: 10px; color: #312e81; font-family: 'Courier New', monospace; }}
  .otp-expire {{ font-size: 0.82rem; color: #ef4444; margin-top: 8px; font-weight: 600; }}
  .warning {{ background: #fffbeb; border-left: 4px solid #f59e0b; padding: 14px 18px; border-radius: 6px; font-size: 0.88rem; color: #92400e; margin-bottom: 24px; }}
  .ignore-note {{ font-size: 0.85rem; color: #9ca3af; line-height: 1.5; }}
  .footer {{ background: #f8fafc; border: 1px solid #e2e8f0; border-top: 0; border-radius: 0 0 12px 12px; padding: 20px 36px; text-align: center; font-size: 0.78rem; color: #9ca3af; }}
  .footer strong {{ color: #6366f1; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>🔧 FixMate</h1>
    <p>Local Service &amp; Booking Platform</p>
  </div>
  <div class="body">
    <p class="greeting">Dear <strong>{user.full_name}</strong>,</p>
    <p class="intro">
      We received a request to reset the password associated with your FixMate account.<br>
      Your One-Time Password (OTP) for password verification is:
    </p>
    <div class="otp-box">
      <div class="otp-label">Your Verification Code</div>
      <div class="otp-code">{otp}</div>
      <div class="otp-expire">⏱ Valid for 5 minutes · Single use only</div>
    </div>
    <div class="warning">
      🔒 <strong>Do not share this code with anyone.</strong>
      FixMate will never ask for your OTP over phone, email or chat.
    </div>
    <p class="ignore-note">
      If you did not request a password reset, please ignore this email.
      Your account password will remain unchanged and no action is required.
    </p>
  </div>
  <div class="footer">
    Regards, <strong>FixMate Support Team</strong><br>
    This is an automated message. Please do not reply to this email.
  </div>
</div>
</body>
</html>
"""
    try:
        from app import mail
        msg = Message(
            subject=subject,
            recipients=[user.email],
            html=html_body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@fixmate.com')
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"[FixMate] OTP email failed for {user.email}: {e}")
        return False


# ---------------------------------------------------------------------------
# Step 1 – Enter Email
# ---------------------------------------------------------------------------
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user)

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        # Validate format
        if not email or not EMAIL_REGEX.match(email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('forgot_password.html')

        user = User.query.filter_by(email=email).first()

        # Security: always show the same neutral message
        if not user:
            flash('If an account is associated with this email address, an OTP has been sent.', 'info')
            return render_template('forgot_password.html')

        # Invalidate any previous active OTP records for this user
        PasswordResetOTP.query.filter_by(user_id=user.id, used=False).update({'used': True})
        db.session.commit()

        # Generate and persist new OTP
        plain_otp = _generate_otp()
        otp_record = PasswordResetOTP.create_for_user(user.id, plain_otp)
        db.session.add(otp_record)
        db.session.commit()

        # Send email
        sent = _send_otp_email(user, plain_otp)

        # Store minimal state in session (no OTP, no raw email)
        session[OTP_SESSION_KEY]  = otp_record.id
        session[OTP_EMAIL_KEY]    = _mask_email(email)
        session[OTP_VERIFIED_KEY] = False
        session[RESEND_AFTER_KEY] = (datetime.utcnow() + timedelta(seconds=60)).isoformat()

        if sent:
            flash('If an account is associated with this email address, an OTP has been sent.', 'info')
        else:
            flash('OTP generated but the email could not be sent. Check server email configuration.', 'warning')

        return redirect(url_for('auth.verify_otp'))

    return render_template('forgot_password.html')


# ---------------------------------------------------------------------------
# Step 2 – Verify OTP
# ---------------------------------------------------------------------------
@auth_bp.route('/forgot-password/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user)

    otp_id = session.get(OTP_SESSION_KEY)
    if not otp_id:
        flash('Session expired. Please start the forgot-password process again.', 'warning')
        return redirect(url_for('auth.forgot_password'))

    otp_record = PasswordResetOTP.query.get(otp_id)
    if not otp_record:
        flash('Invalid session. Please start again.', 'warning')
        return redirect(url_for('auth.forgot_password'))

    masked_email = session.get(OTP_EMAIL_KEY, '***')

    # Calculate seconds remaining for the countdown
    now = datetime.utcnow()
    seconds_left = max(0, int((otp_record.expires_at - now).total_seconds()))

    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()

        if not otp_record.is_valid:
            if otp_record.is_expired:
                flash('This OTP has expired. Please request a new OTP.', 'danger')
            elif otp_record.attempts >= 5:
                flash('Too many incorrect attempts. Please request a new OTP.', 'danger')
            else:
                flash('This OTP has already been used. Please request a new OTP.', 'danger')
            return render_template('verify_otp.html',
                                   masked_email=masked_email,
                                   seconds_left=0)

        if not entered_otp or len(entered_otp) != 6 or not entered_otp.isdigit():
            flash('Please enter the 6-digit OTP.', 'danger')
            return render_template('verify_otp.html',
                                   masked_email=masked_email,
                                   seconds_left=seconds_left)

        if otp_record.verify_otp(entered_otp):
            # Mark OTP as used (but NOT permanently consumed yet — consumed on password save)
            session[OTP_VERIFIED_KEY] = True
            db.session.commit()
            flash('OTP verified successfully. Please create your new password.', 'success')
            return redirect(url_for('auth.reset_password'))
        else:
            db.session.commit()  # persist incremented attempts
            remaining = 5 - otp_record.attempts
            if remaining <= 0:
                otp_record.used = True
                db.session.commit()
                flash('Too many incorrect attempts. The OTP has been invalidated. Please request a new one.', 'danger')
                return render_template('verify_otp.html',
                                       masked_email=masked_email,
                                       seconds_left=0)
            flash(f'Invalid OTP. Please check the code and try again. ({remaining} attempt{"s" if remaining != 1 else ""} left)', 'danger')
            return render_template('verify_otp.html',
                                   masked_email=masked_email,
                                   seconds_left=seconds_left)

    return render_template('verify_otp.html',
                           masked_email=masked_email,
                           seconds_left=seconds_left)


# ---------------------------------------------------------------------------
# Step 2b – Resend OTP (with 60-second cooldown)
# ---------------------------------------------------------------------------
@auth_bp.route('/forgot-password/resend-otp', methods=['POST'])
def resend_otp():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user)

    otp_id = session.get(OTP_SESSION_KEY)
    if not otp_id:
        flash('Session expired. Please start again.', 'warning')
        return redirect(url_for('auth.forgot_password'))

    old_record = PasswordResetOTP.query.get(otp_id)
    if not old_record:
        flash('Invalid session. Please start again.', 'warning')
        return redirect(url_for('auth.forgot_password'))

    # Enforce 60-second cooldown
    resend_after_str = session.get(RESEND_AFTER_KEY)
    if resend_after_str:
        resend_after = datetime.fromisoformat(resend_after_str)
        if datetime.utcnow() < resend_after:
            wait = int((resend_after - datetime.utcnow()).total_seconds())
            flash(f'Please wait {wait} second{"s" if wait != 1 else ""} before requesting a new OTP.', 'warning')
            return redirect(url_for('auth.verify_otp'))

    user = old_record.user

    # Invalidate old OTP
    old_record.used = True
    db.session.commit()

    # Generate fresh OTP
    plain_otp = _generate_otp()
    new_record = PasswordResetOTP.create_for_user(user.id, plain_otp)
    db.session.add(new_record)
    db.session.commit()

    sent = _send_otp_email(user, plain_otp)

    # Update session
    session[OTP_SESSION_KEY]  = new_record.id
    session[OTP_VERIFIED_KEY] = False
    session[RESEND_AFTER_KEY] = (datetime.utcnow() + timedelta(seconds=60)).isoformat()

    if sent:
        flash('A new OTP has been sent to your registered email address.', 'success')
    else:
        flash('OTP generated but the email could not be sent. Check server email configuration.', 'warning')

    return redirect(url_for('auth.verify_otp'))


# ---------------------------------------------------------------------------
# Step 3 – Create New Password
# ---------------------------------------------------------------------------
@auth_bp.route('/forgot-password/reset', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user)

    # Gate: OTP must have been verified in this session
    if not session.get(OTP_VERIFIED_KEY):
        flash('Please verify your OTP before resetting the password.', 'warning')
        return redirect(url_for('auth.forgot_password'))

    otp_id = session.get(OTP_SESSION_KEY)
    if not otp_id:
        flash('Session expired. Please start again.', 'warning')
        return redirect(url_for('auth.forgot_password'))

    otp_record = PasswordResetOTP.query.get(otp_id)
    if not otp_record or otp_record.used:
        flash('Your session is no longer valid. Please start again.', 'warning')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password     = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Password complexity (same as registration)
        if (len(new_password) < 8
                or not re.search(r'[A-Z]', new_password)
                or not re.search(r'[a-z]', new_password)
                or not re.search(r'\d', new_password)):
            flash('Password must contain at least 8 characters, including uppercase, lowercase and a number.', 'danger')
            return render_template('reset_password.html')

        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html')

        # Update password using existing hashing system
        user = otp_record.user
        user.set_password(new_password)

        # Consume OTP permanently
        otp_record.used = True
        db.session.commit()

        # Clear all forgot-password session keys
        for key in (OTP_SESSION_KEY, OTP_EMAIL_KEY, OTP_VERIFIED_KEY, RESEND_AFTER_KEY):
            session.pop(key, None)

        flash('Your password has been reset successfully. Please log in with your new password.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html')


def redirect_role_dashboard(user):
    if user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif user.role == 'provider':
        return redirect(url_for('provider.dashboard'))
    else:
        return redirect(url_for('customer.dashboard'))
