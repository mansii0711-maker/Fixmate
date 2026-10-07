// Authentication & Registration Form Validation Script

function switchRegisterTab(role) {
    const customerForm = document.getElementById('customer-form');
    const providerForm = document.getElementById('provider-form');
    const roleInput = document.getElementById('role-hidden-input');
    
    const customerTabBtn = document.getElementById('tab-btn-customer');
    const providerTabBtn = document.getElementById('tab-btn-provider');

    // Provider fields requiring mandatory validation when Provider role is active
    const expInput = document.getElementById('experience');
    const catSelect = document.getElementById('category_id');
    const qualInput = document.getElementById('qualification');
    const areaInput = document.getElementById('operating_area');

    if (role === 'customer') {
        customerForm.style.display = 'block';
        providerForm.style.display = 'none';
        roleInput.value = 'customer';

        customerTabBtn.classList.add('active');
        providerTabBtn.classList.remove('active');

        // Remove provider required attributes
        if (expInput) expInput.removeAttribute('required');
        if (catSelect) catSelect.removeAttribute('required');
        if (qualInput) qualInput.removeAttribute('required');
        if (areaInput) areaInput.removeAttribute('required');
    } else {
        customerForm.style.display = 'none';
        providerForm.style.display = 'block';
        roleInput.value = 'provider';

        providerTabBtn.classList.add('active');
        customerTabBtn.classList.remove('active');

        // Add provider required attributes
        if (expInput) expInput.setAttribute('required', 'true');
        if (catSelect) catSelect.setAttribute('required', 'true');
        if (qualInput) qualInput.setAttribute('required', 'true');
        if (areaInput) areaInput.setAttribute('required', 'true');
    }
}

// Quick Demo Login Helper for Viva Presentation
function fillDemoAccount(email, password) {
    const emailField = document.getElementById('email');
    const passwordField = document.getElementById('password');
    if (emailField && passwordField) {
        emailField.value = email;
        passwordField.value = password;
    }
}

// Client-side Validation Handlers
document.addEventListener('DOMContentLoaded', () => {
    // 1. File Upload Name Display
    const fileInput = document.getElementById('verification_doc');
    const fileNameDisplay = document.getElementById('file-name-display');

    if (fileInput && fileNameDisplay) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                const validTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
                
                if (!validTypes.includes(file.type)) {
                    alert('Invalid file format. Please upload a PDF, PNG, JPG, or DOC file.');
                    fileInput.value = '';
                    fileNameDisplay.textContent = 'Mandatory for Provider verification. Max size: 16 MB';
                    fileNameDisplay.style.color = 'var(--gray-600)';
                    return;
                }

                fileNameDisplay.textContent = '✓ Document Uploaded: ' + file.name;
                fileNameDisplay.style.color = '#059669';
                fileNameDisplay.style.fontWeight = '700';
            }
        });
    }

    // 2. Real-time Password Matching Indicator
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    const matchMsg = document.getElementById('password-match-msg');

    function validatePasswordMatch() {
        if (!passwordInput || !confirmPasswordInput || !matchMsg) return;
        if (confirmPasswordInput.value.length === 0) {
            matchMsg.textContent = '';
            return;
        }

        if (passwordInput.value === confirmPasswordInput.value) {
            matchMsg.textContent = '✓ Passwords match';
            matchMsg.style.color = '#059669';
        } else {
            matchMsg.textContent = '✗ Passwords do not match';
            matchMsg.style.color = '#ef4444';
        }
    }

    if (passwordInput && confirmPasswordInput) {
        passwordInput.addEventListener('input', validatePasswordMatch);
        confirmPasswordInput.addEventListener('input', validatePasswordMatch);
    }
});
