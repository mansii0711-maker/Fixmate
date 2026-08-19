# Project Synopsis: FixMate – Local Service Booking Platform

## 1. Project Title & Abstract
**Project Title:** FixMate – On-Demand Local Service & Booking Web Application  
**Target Domain:** Web Development / E-Commerce / Service Automation  
**Target Audience:** Customers, Local Service Providers (Electricians, Plumbers, Carpenters, Tutors, etc.), Platform Administrator  

**Abstract:**  
Access to reliable local service professionals currently relies on unorganized, informal contacts and word-of-mouth referrals. This leads to lack of pricing transparency, scheduling delays, and trust issues. **FixMate** is a web-based role-based platform designed to organize and streamline local service discovery, booking, and payment. Customers can discover verified service providers, compare pricing, choose convenient time slots, and pay securely online. Service providers get a dedicated dashboard to list services, set pricing, manage availability, and track earnings. An Admin panel oversees provider verification and platform metrics. Built with **HTML/CSS/JS (Frontend)**, **Python/Flask (Backend)**, and **MySQL (Database)**, FixMate provides a transparent, accountable, and scalable solution for local service commerce.

---

## 2. Problem Statement
In local Indian / regional markets, finding trustworthy service professionals (e.g., plumbers, electricians, home tutors) involves multiple challenges:
* **Lack of Transparency:** No standard pricing, leading to price ambiguity and overcharging.
* **Inconvenient Booking & Unreliable Scheduling:** Absence of structured appointment booking leads to missed or delayed service visits.
* **Low Visibility for Independent Workers:** Skilled local technicians lack digital presence and exposure to nearby clients.
* **No Quality Assurance / Trust Mechanism:** Absence of centralized accountability, review system, or background verification status.

---

## 3. Objectives of the Project
1. **Multi-Role System:** Develop a secure, role-based platform supporting **Customers**, **Service Providers**, and **Admins**.
2. **Profile & Service Management:** Enable service providers to showcase their skills, set custom rates, and manage service availability.
3. **Smart Search & Area Filtering:** Allow customers to find providers based on service category, city/area, rating, and price.
4. **Interactive Slot Booking:** Build an automated booking system tracking real-time status (`Pending` $\rightarrow$ `Confirmed` $\rightarrow$ `Completed` $\rightarrow$ `Cancelled`).
5. **Integrated Payment Handling:** Incorporate online payment options (Razorpay/Stripe Test Mode) along with Cash-on-Service options.
6. **Reviews & Feedback System:** Enable post-service ratings and reviews to maintain service quality standards.
7. **Admin Oversight & Verification:** Implement an admin module to review provider applications, verify documents, and monitor platform analytics.

---

## 4. System Architecture & Proposed Modules

### Module 1: Authentication & Role-Based Access Control (RBAC)
* User registration & login with secure password hashing (`Werkzeug` / `Bcrypt`).
* Role identification (`Customer`, `Provider`, `Admin`) directing users to customized dashboards.
* Session management and route protection (`Flask-Login` / `PyJWT`).

### Module 2: Provider Management & Service Catalog
* Provider profile setup: Bio, experience, qualification proof, contact info, operating area.
* Service listing CRUD (Create, Read, Update, Pause/Activate service listings).
* Categorized listing (Electrician, Plumber, Carpenter, Appliance Repair, Home Tutor, Cleaning).

### Module 3: Customer Discovery & Search Engine
* Multi-criteria filtering: Search by Category, Area/City, Price range, and User ratings.
* Service detail page with transparent pricing breakdown and provider credentials.

### Module 4: Booking & Slot Scheduling System
* Time-slot selection based on provider availability.
* Real-time booking status flow:
  $$\text{Pending} \longrightarrow \text{Confirmed (Provider Accepted)} \longrightarrow \text{Completed} / \text{Cancelled}$$
* Automated booking summary and status notifications.

### Module 5: Payment Gateway & Invoicing
* Integrated online payment gateway using **Razorpay / Stripe SDK (Test Sandbox Mode)**.
* Support for **Cash on Service (CoS)** / Pay After Service.
* Digital invoice generation upon successful completion.

### Module 6: Ratings & Reviews Module
* Verified customer reviews upon booking completion.
* Dynamic overall rating calculation displayed on provider profile.

### Module 7: Dashboards & Admin Control Panel
* **Customer Dashboard:** Active bookings, past history, payment statuses, rating options.
* **Provider Dashboard:** Incoming booking requests (Accept/Reject), schedule view, revenue overview, active services.
* **Admin Dashboard:** Approve/Reject new provider registrations, view total metrics (users, services, bookings, total platform revenue), handle user suspensions.

---

## 5. Scope of the Project
* **Functional Boundaries:** Supports primary household & personal service categories within selected cities/areas.
* **Location Handling:** Uses area/pincode selection rather than real-time GPS tracking for simplicity.
* **Payment Mode:** Sandbox / Test API integration for academic demonstration.
* **Target Environment:** Standard desktop and modern mobile web browsers.

---

## 6. Technical Stack

| Layer | Technology Used | Description / Purpose |
| :--- | :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (ES6) | Responsive, modern user interface, dynamic DOM interactions |
| **Backend** | Python 3.x, Flask Framework | RESTful routes, request handling, business logic, session control |
| **Database** | MySQL | Relational data storing users, services, bookings, reviews, payments |
| **ORM / Driver** | Flask-SQLAlchemy / PyMySQL | Python object-relational mapping for secure DB operations |
| **Payment API** | Razorpay SDK / Stripe API | Test-mode payment gateway integration |

---

## 7. Future Enhancements
1. **Geolocation & Google Maps API:** Live distance calculation and route tracking for service arrival.
2. **In-App Messaging & Calling:** Direct chat between customer and provider post-confirmation.
3. **AI-Based Provider Recommendations:** Smart matching based on provider ratings, proximity, and customer preference history.
4. **Mobile Application:** Native Android / iOS application using React Native or Flutter.

---

## 8. Conclusion
**FixMate** effectively bridges the gap between local service providers and home customers by substituting fragmented offline referrals with a centralized, reliable web application. By offering role-based management, transparent pricing, appointment slot booking, sandbox payment capabilities, and administrative quality control, FixMate presents a robust end-to-end prototype suitable for modern urban service needs.
