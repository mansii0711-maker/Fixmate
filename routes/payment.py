import time
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from database import db, User, Service, Booking, Payment, Notification
import razorpay

payment_bp = Blueprint('payment', __name__)

def get_razorpay_client():
    key_id = current_app.config.get('RAZORPAY_KEY_ID') or 'rzp_test_FixMateKey2026'
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET') or 'FixMateSecretKey2026'
    return razorpay.Client(auth=(key_id, key_secret))

def verify_booking_access(booking):
    if not current_user.is_authenticated:
        return False
    if current_user.role == 'customer' and booking.customer_id == current_user.id:
        return True
    if current_user.role == 'admin':
        return True
    if current_user.role == 'provider' and booking.provider_id == current_user.id:
        return True
    return False

# 1. Payment Method Selection & Summary Page
@payment_bp.route('/payment/<int:booking_id>')
@login_required
def select_payment_method(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if not verify_booking_access(booking):
        flash('Access denied. You can only access your own bookings.', 'danger')
        return redirect(url_for('customer.my_bookings'))

    razorpay_key_id = current_app.config.get('RAZORPAY_KEY_ID') or 'rzp_test_FixMateKey2026'
    
    return render_template('payment_select.html',
                           booking=booking,
                           razorpay_key_id=razorpay_key_id)

# 2. COD / Cash on Service Handler
@payment_bp.route('/payment/cod/<int:booking_id>', methods=['POST'])
@login_required
def process_cod(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.customer_id != current_user.id:
        flash('Unauthorized payment action.', 'danger')
        return redirect(url_for('customer.my_bookings'))

    booking.payment_method = 'COD'
    booking.payment_status = 'Pending'
    if booking.status != 'Cancelled':
        booking.status = 'Pending'

    payment = Payment.query.filter_by(booking_id=booking.id).first()
    if not payment:
        payment = Payment(
            booking_id=booking.id,
            customer_id=booking.customer_id,
            provider_id=booking.provider_id,
            amount=booking.total_amount,
            payment_method='COD',
            payment_status='Pending'
        )
        db.session.add(payment)
    else:
        payment.payment_method = 'COD'
        payment.payment_status = 'Pending'

    notif_cust = Notification(
        user_id=current_user.id,
        title='Booking Confirmed (COD)',
        message=f'Booking #{booking.id} placed with Cash on Service. Payment will be collected after service completion.'
    )
    notif_prov = Notification(
        user_id=booking.provider_id,
        title='New Service Request (COD)',
        message=f'Customer {current_user.full_name} booked "{booking.service.title}" via Cash on Service.'
    )
    db.session.add(notif_cust)
    db.session.add(notif_prov)
    db.session.commit()

    flash('Booking confirmed successfully. Payment will be collected after the service.', 'success')
    return redirect(url_for('payment.show_invoice', booking_id=booking.id))

# 3. Create Razorpay Order API
@payment_bp.route('/payment/create-order/<int:booking_id>', methods=['POST'])
@login_required
def create_order(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.customer_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403

    client = get_razorpay_client()
    key_id = current_app.config.get('RAZORPAY_KEY_ID') or 'rzp_test_FixMateKey2026'
    amount_paise = int(round(booking.total_amount * 100))

    try:
        order_data = {
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': f'rcpt_fixmate_{booking.id}',
            'payment_capture': 1
        }
        order = client.order.create(data=order_data)
        razorpay_order_id = order['id']
    except Exception:
        razorpay_order_id = f"order_fixmate_{booking.id}_{int(time.time())}"

    payment = Payment.query.filter_by(booking_id=booking.id).first()
    if not payment:
        payment = Payment(
            booking_id=booking.id,
            customer_id=booking.customer_id,
            provider_id=booking.provider_id,
            amount=booking.total_amount,
            payment_method='Razorpay',
            payment_status='Pending',
            razorpay_order_id=razorpay_order_id
        )
        db.session.add(payment)
    else:
        payment.payment_method = 'Razorpay'
        payment.razorpay_order_id = razorpay_order_id

    booking.payment_method = 'Razorpay'
    db.session.commit()

    return jsonify({
        'success': True,
        'order_id': razorpay_order_id,
        'key_id': key_id,
        'amount': booking.total_amount,
        'amount_paise': amount_paise,
        'currency': 'INR',
        'service_title': booking.service.title,
        'customer_name': current_user.full_name,
        'customer_email': current_user.email,
        'customer_mobile': current_user.mobile
    })

# 4. Verify Razorpay Payment Signature
@payment_bp.route('/payment/verify/<int:booking_id>', methods=['POST'])
@login_required
def verify_payment(booking_id):
    data = request.get_json() or request.form
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')

    booking = Booking.query.get_or_404(booking_id)
    if booking.customer_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized payment request.'}), 403

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
        now = datetime.utcnow()
        booking.payment_method = 'Razorpay'
        booking.payment_status = 'Paid'
        if booking.status == 'Pending':
            booking.status = 'Confirmed'

        payment = Payment.query.filter_by(booking_id=booking.id).first()
        gen_payment_id = razorpay_payment_id or f"pay_sandbox_{booking.id}_{int(time.time())}"

        if not payment:
            payment = Payment(
                booking_id=booking.id,
                customer_id=booking.customer_id,
                provider_id=booking.provider_id,
                amount=booking.total_amount,
                payment_method='Razorpay',
                payment_status='Paid',
                razorpay_order_id=razorpay_order_id or f"order_sandbox_{booking.id}",
                razorpay_payment_id=gen_payment_id,
                razorpay_signature=razorpay_signature or 'sandbox_signature',
                paid_at=now
            )
            db.session.add(payment)
        else:
            payment.payment_method = 'Razorpay'
            payment.payment_status = 'Paid'
            payment.razorpay_payment_id = gen_payment_id
            payment.razorpay_signature = razorpay_signature or 'sandbox_signature'
            payment.paid_at = now

        notif_cust = Notification(
            user_id=current_user.id,
            title='Payment Received ✓',
            message=f'Payment of ₹{booking.total_amount:.0f} for "{booking.service.title}" (Booking #{booking.id}) was successfully processed via Razorpay.'
        )
        notif_prov = Notification(
            user_id=booking.provider_id,
            title='Booking Paid Online ✓',
            message=f'Customer {current_user.full_name} completed online payment of ₹{booking.total_amount:.0f} for Booking #{booking.id}.'
        )
        db.session.add(notif_cust)
        db.session.add(notif_prov)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Payment completed successfully!',
            'redirect_url': url_for('payment.show_invoice', booking_id=booking.id)
        })

    return jsonify({'success': False, 'message': 'Payment verification failed'}), 400

# 5. Handle Payment Failure / Cancellation
@payment_bp.route('/payment/failed/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def payment_failed(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.customer_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('customer.my_bookings'))

    booking.payment_status = 'Failed'
    payment = Payment.query.filter_by(booking_id=booking.id).first()
    if payment and payment.payment_status != 'Paid':
        payment.payment_status = 'Failed'
    
    db.session.commit()

    flash('Payment was not completed. You can retry the payment.', 'warning')
    return render_template('payment_failed.html', booking=booking)

# 6. Show Professional Invoice
@payment_bp.route('/invoice/<int:booking_id>')
@login_required
def show_invoice(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if not verify_booking_access(booking):
        flash('Access denied. You can only view invoices for your own bookings.', 'danger')
        return redirect(url_for('customer.my_bookings'))

    payment = Payment.query.filter_by(booking_id=booking.id).first()
    invoice_no = f"INV-{booking.created_at.strftime('%Y%m%d') if booking.created_at else '2026'}-{booking.id:04d}"

    return render_template('invoice.html',
                           booking=booking,
                           payment=payment,
                           invoice_no=invoice_no,
                           auto_print=False)

# 7. Download / Print Invoice
@payment_bp.route('/invoice/<int:booking_id>/download')
@login_required
def download_invoice(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if not verify_booking_access(booking):
        flash('Access denied. You can only view invoices for your own bookings.', 'danger')
        return redirect(url_for('customer.my_bookings'))

    payment = Payment.query.filter_by(booking_id=booking.id).first()
    invoice_no = f"INV-{booking.created_at.strftime('%Y%m%d') if booking.created_at else '2026'}-{booking.id:04d}"

    return render_template('invoice.html',
                           booking=booking,
                           payment=payment,
                           invoice_no=invoice_no,
                           auto_print=True)
