from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from flask_mysqldb import MySQL
import random
import re
import os
import qrcode
from datetime import datetime, timedelta
import re


from flask import Flask, render_template, request, redirect, session, flash
from flask_mail import Mail, Message
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# MAIL CONFIG
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'healcarehms@gmail.com'
app.config['MAIL_PASSWORD'] = 'vjrdrfhxbundinen'   # ⚠️ not normal gmail password
app.config['MAIL_DEFAULT_SENDER'] = 'healcarehms@gmail.com'

mail = Mail(app)



app.secret_key = "secret"

# MYSQL CONFIG
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'admin'
app.config['MYSQL_DB'] = 'hospital'

mysql = MySQL(app)


# Home Page
@app.route('/')
def home():
    return render_template("login.html")



# ADMIN LOGIN
@app.route('/admin_login', methods=['POST'])
def admin_login():

    username = request.form['username']
    password = request.form['password']

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT * FROM admins
        WHERE username=%s AND password=%s AND status='Active'
    """, (username, password))

    admin = cur.fetchone()
    cur.close()

    if admin:
        session['admin_id'] = admin[0]       # admin id
        session['admin'] = admin[1]          # username
        session['admin_status'] = admin[3]

        return redirect('/admin_dashboard')

    return render_template("login.html", admin_error="Invalid or Inactive Admin")

@app.route('/admin_create')
def admin_create():
    return render_template("admin.html")

@app.route('/delete_admin/<int:id>', methods=['POST'])
def delete_admin(id):
    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM admins WHERE admin_id = %s", (id,))
    mysql.connection.commit()

    cur.close()

    return redirect('/admin_profile')

@app.route('/admin_profile', methods=['GET','POST'])
def admin_profile():

    if 'admin' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    # Create new admin
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur.execute("""
        INSERT INTO admins(username,password,status)
        VALUES(%s,%s,'Inactive')
        """,(username,password))

        mysql.connection.commit()

    # Get all admins
    cur.execute("SELECT * FROM admins")
    admins = cur.fetchall()

    cur.close()

    return render_template("admin_profile.html", admins=admins)

@app.route('/logout')
def logout():
        session.clear()
        return redirect('/')


@app.route('/toggle_admin/<int:id>')
def toggle_admin(id):

    cur = mysql.connection.cursor()

    cur.execute("SELECT status FROM admins WHERE admin_id=%s",(id,))
    status = cur.fetchone()[0]

    new_status = 'Inactive' if status == 'Active' else 'Active'

    cur.execute("UPDATE admins SET status=%s WHERE admin_id=%s",(new_status,id))
    mysql.connection.commit()
    cur.close()

    return redirect('/admin_profile')

@app.route('/admin_dashboard')
def admin_dashboard():

    if 'admin' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    # Basic Counts
    cur.execute("SELECT COUNT(*) FROM doctors")
    doctors = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM patients")
    patients = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments")
    appointments = cur.fetchone()[0]

    # Status Counts
    cur.execute("SELECT COUNT(*) FROM appointments WHERE status='Pending'")
    pending = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments WHERE status='Approved'")
    approved = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments WHERE status='Canceled'")
    cancelled = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments WHERE status='Rejected'")
    rejected = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments WHERE status='Finished'")
    finished = cur.fetchone()[0]

    # Today Data
    cur.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date = CURDATE()")
    today_appointments = cur.fetchone()[0]

    # Departments
    cur.execute("SELECT COUNT(DISTINCT specialization) FROM doctors")
    departments = cur.fetchone()[0]
     
     

     # 👨‍⚕️ Available Doctors
    cur.execute("SELECT COUNT(*) FROM doctors WHERE status='Active'")
    available_doctors = cur.fetchone()[0]

    # 🔔 Notifications
    notifications = []

    if pending > 0:
     notifications.append({
        "text": f"{pending} appointments pending",
        "link": url_for('admin_view_appointments')
    })

    if today_appointments > 0:
     notifications.append({
        "text": f"{today_appointments} appointments today",
        "link": url_for('admin_view_appointments')
    })

    if available_doctors < doctors:
     notifications.append({
        "text": "Some doctors are inactive",
        "link": url_for('manage_doctors')
    })

    if len(notifications) == 0:
     notifications.append({
        "text": "All systems running smoothly",
        "link": "#"
    })

# 🧑 Today Patients (unique patients today)
    cur.execute("""
    SELECT COUNT(DISTINCT patient_id)
    FROM appointments
    WHERE appointment_date = CURDATE()
""")
    today_patients = cur.fetchone()[0]
    # Revenue
   
   

    # Recent Appointments
    cur.execute("""
        SELECT name, doctor_name, appointment_date, status
        FROM appointments
        ORDER BY appointment_date DESC
        LIMIT 5
    """)
    recent = cur.fetchall()

    cur.close()

    return render_template(
    "admin_dashboard.html",
    doctors=doctors,
    patients=patients,
    appointments=appointments,
    pending=pending,
    approved=approved,
    cancelled=cancelled,
    rejected=rejected,
    finished=finished,
    today_appointments=today_appointments,
    departments=departments,

    # ✅ NEW FIELDS
    available_doctors=available_doctors,
    today_patients=today_patients,
    notifications=notifications,

    recent=recent
)

import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/add_doctor', methods=['GET','POST'])
def add_doctor():

    if request.method == 'POST':

        cur = mysql.connection.cursor()

        name = request.form.get('name')
        specialization = request.form.get('specialization')
        phone = request.form.get('phone')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        shift_start_hm = request.form.get('shift_start_hm')
        shift_end_hm = request.form.get('shift_end_hm')
        shift_type = request.form.get('shift_type')

        # ✅ PROFILE IMAGE
        profile_pic = request.files.get('profile_pic')
        filename = None

        if profile_pic and profile_pic.filename != "":
            filename = secure_filename(profile_pic.filename)
            profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # ✅ PASSWORD CHECK
        if password != confirm_password:
            return "Password mismatch"

        # ✅ GENERATE ID
        cur.execute("SELECT doctor_id FROM doctors ORDER BY doctor_id DESC LIMIT 1")
        last = cur.fetchone()

        if last:
            new_id = int(last[0][1:]) + 1
        else:
            new_id = 1

        doctor_id = "D" + str(new_id).zfill(3)

        try:
            cur.execute("""
            INSERT INTO doctors
            (doctor_id,name,specialization,phone,email,username,password,
             shift_start_hm,shift_end_hm,shift_type,profile_pic)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,(doctor_id,name,specialization,phone,email,username,password,
                 shift_start_hm,shift_end_hm,shift_type,filename))

            mysql.connection.commit()

            flash(f"Doctor Registered Successfully! Doctor ID: {doctor_id}", "success")

        except Exception as e:
            mysql.connection.rollback()
            return str(e)

        return redirect('/add_doctor')

    return render_template("add_doctor.html")

# MANAGE DOCTORS
@app.route('/manage_doctors')
def manage_doctors():
    cur = mysql.connection.cursor()

    # ✅ HANDLE UPDATE
    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']
        specialization = request.form['specialization']
        shift_type = request.form['shift_type']
        shift_start = request.form['shift_start_hm']
        shift_end = request.form['shift_end_hm']

        cursor.execute("""
       UPDATE doctors 
SET name=%s, email=%s, phone=%s, username=%s, password=%s,
    specialization=%s, shift_start_hm=%s, shift_end_hm=%s, shift_type=%s,
    profile_pic=%s
WHERE doctor_id=%s
""", (name, email, phone, username, password,
      specialization, shift_start, shift_end, shift_type,
       doctor_id))
        
        mysql.connection.commit()

    # ✅ FETCH DATA AFTER UPDATE
    cur.execute("SELECT * FROM doctors")
    doctors = cur.fetchall()

    cur.close()

    return render_template("manage_doctors.html", doctors=doctors)


# MANAGE PATIENTS
@app.route('/manage_patients')
def manage_patients():

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM patients")
    patients = cur.fetchall()

    return render_template("manage_patients.html", patients=patients)


# VIEW APPOINTMENTS
@app.route('/view_appointments')
def admin_view_appointments():

    if 'admin' not in session:
        return redirect('/')

    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    doctor_id = request.args.get('doctor_id')
    department = request.args.get('department')

    cur = mysql.connection.cursor()

    # Get doctors for filter dropdown
    cur.execute("SELECT doctor_id, name FROM doctors")
    doctors = cur.fetchall()

    # Get departments for filter dropdown
    cur.execute("SELECT DISTINCT specialization FROM doctors")
    departments = [d[0] for d in cur.fetchall()]

    query = """
    SELECT *
    FROM appointments
    WHERE 1=1
    """

    params = []

    if from_date and to_date:
        query += " AND appointment_date BETWEEN %s AND %s"
        params.append(from_date)
        params.append(to_date)

    if doctor_id:
        query += " AND doctor_id=%s"
        params.append(doctor_id)

    if department:
        query += " AND specialization=%s"
        params.append(department)

    query += """
ORDER BY 
CASE 
    WHEN status = 'Pending' THEN 1
    WHEN status = 'Approved' THEN 2
    WHEN status = 'Finished' THEN 3
    WHEN status IN ('Rejected','Canceled') THEN 4
    ELSE 5
END,
appointment_date DESC,
appointment_time DESC
"""

    cur.execute(query, tuple(params))
    appointments = cur.fetchall()

    cur.close()

    return render_template(
    "view_appointments.html",
    appointments=appointments,
    doctors=doctors,
    departments=departments,
    selected_doctor=request.args.get('doctor_id')  # ✅ ADD THIS
)



@app.route('/admin_search')
def admin_search():

    if 'admin' not in session:
        return redirect('/')

    query = request.args.get('query')

    cur = mysql.connection.cursor()

    patient = None
    doctor = None
    patient_appointments = []
    doctor_appointments = []
    reports = []

    # 🔍 Search Patient
    cur.execute("SELECT * FROM patients WHERE patient_id=%s", (query,))
    patient = cur.fetchone()

    # 🔍 Patient Appointments
    if patient:
        cur.execute("""
            SELECT token, doctor_name, specialization,
                   appointment_date, appointment_time, status
            FROM appointments
            WHERE patient_id=%s
            ORDER BY appointment_date DESC
        """, (query,))
        patient_appointments = cur.fetchall()

        # 📝 Patient Reports
        cur.execute("""
            SELECT doctor_name, department, report_text, report_date
            FROM patient_reports
            WHERE patient_id=%s
        """, (query,))
        reports = cur.fetchall()

    # 🔍 Search Doctor
    cur.execute("""
        SELECT * FROM doctors 
        WHERE doctor_id=%s OR name LIKE %s
    """, (query, "%" + query + "%"))
    doctor = cur.fetchone()

    # 🔍 Doctor Appointments
    if doctor:
        cur.execute("""
            SELECT name, appointment_date, appointment_time, status
            FROM appointments
            WHERE doctor_id=%s
            ORDER BY appointment_date DESC
        """, (doctor[0],))
        doctor_appointments = cur.fetchall()

    cur.close()

    return render_template(
        "admin_search.html",
        patient=patient,
        doctor=doctor,
        query=query,
        patient_appointments=patient_appointments,
        doctor_appointments=doctor_appointments,
        reports=reports
    )



from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import qrcode
import os

@app.route('/download_report/<query>')
def download_report(query):

    cur = mysql.connection.cursor()

    # Patient
    cur.execute("SELECT * FROM patients WHERE patient_id=%s", (query,))
    patient = cur.fetchone()

    # Doctor
    cur.execute("""
        SELECT * FROM doctors 
        WHERE doctor_id=%s OR name LIKE %s
    """, (query, "%" + query + "%"))
    doctor = cur.fetchone()
    # 📝 Patient Reports (ADD THIS)
    cur.execute("""
    SELECT doctor_name, department, report_text, report_date
    FROM patient_reports
    WHERE patient_id=%s
""", (query,))
    reports = cur.fetchall()
    # Appointment History
    cur.execute("""
        SELECT doctor_name, specialization, appointment_date, status
        FROM appointments
        WHERE patient_id=%s
        ORDER BY appointment_date DESC
    """, (query,))
    appointments = cur.fetchall()

    cur.close()

    filename = f"report_{query}.pdf"
    filepath = "static/" + filename

    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []


    # 🖼️ LOGO
    if os.path.exists("static/logo.png"):
        logo = Image("static/logo.png", width=80, height=80)
        elements.append(logo)

    # 🏥 HEADER
    elements.append(Paragraph("HEAL CARE HOSPITAL", styles['Title']))
    elements.append(Paragraph("Patient Full Report", styles['Normal']))
    elements.append(Spacer(1, 20))

    # 🧑 PATIENT TABLE
    if patient:
        elements.append(Paragraph("Patient Details", styles['Heading2']))

        data = [
            ["Field", "Details"],
            ["Patient ID", patient[0]],
            ["Name", patient[1]],
            ["Age", str(patient[2])],
            ["Phone", patient[3]],
        ]

        table = Table(data, colWidths=[150, 250])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
            ('GRID', (0,0), (-1,-1), 1, colors.grey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

    # 👨‍⚕️ DOCTOR TABLE
    if doctor:
        elements.append(Paragraph("Doctor Details", styles['Heading2']))

        data = [
            ["Field", "Details"],
            ["Doctor ID", doctor[0]],
            ["Name", doctor[1]],
            ["Specialization", doctor[6]],
            ["Phone", doctor[3]],
        ]

        table = Table(data, colWidths=[150, 250])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgreen),
            ('GRID', (0,0), (-1,-1), 1, colors.grey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

    # 📊 APPOINTMENT HISTORY
    if appointments:
        elements.append(Paragraph("Appointment History", styles['Heading2']))

        appt_data = [["Doctor", "Department", "Date", "Status"]]

        for a in appointments:
            appt_data.append([
                a[0], a[1], str(a[2]), a[3]
            ])

        table = Table(appt_data, colWidths=[120, 120, 100, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.orange),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))



    # 🧾 QR CODE
    qr_data = f"Patient ID: {query}"
    qr_img = qrcode.make(qr_data)

    qr_path = f"static/qr_{query}.png"
    qr_img.save(qr_path)

    qr = Image(qr_path, width=100, height=100)

    elements.append(Paragraph("Scan QR for Patient Info", styles['Normal']))
    elements.append(qr)
    elements.append(Spacer(1, 20))

    # ✍️ SIGNATURE
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("Doctor Signature:", styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("__________________________", styles['Normal']))

    # 📅 FOOTER
    from datetime import datetime
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
        styles['Normal']
    ))

    doc.build(elements)

    return redirect("/" + filepath)
    

from flask import jsonify

@app.route('/live_search')
def live_search():

    query = request.args.get('q')

    cur = mysql.connection.cursor()

    results = []

    # 🔍 Patients
    cur.execute("""
        SELECT patient_id, name 
        FROM patients 
        WHERE patient_id LIKE %s OR name LIKE %s
        LIMIT 5
    """, ("%" + query + "%", "%" + query + "%"))

    for p in cur.fetchall():
        results.append({
            "label": f"{p[0]} ( {p[1]} )",
            "value": p[0]
        })

    # 🔍 Doctors
    cur.execute("""
        SELECT doctor_id, name 
        FROM doctors 
        WHERE doctor_id LIKE %s OR name LIKE %s
        LIMIT 5
    """, ("%" + query + "%", "%" + query + "%"))

    for d in cur.fetchall():
        results.append({
            "label": f"{d[0]} ( {d[1]} )",
            "value": d[0]
        })

    cur.close()

    return jsonify(results) 

# REPORTS
@app.route("/reports")
def reports():

    cur = mysql.connection.cursor()

    # Total Patients
    cur.execute("SELECT COUNT(*) FROM patients")
    patients = cur.fetchone()[0]

    # Total Doctors
    cur.execute("SELECT COUNT(*) FROM doctors")
    doctors = cur.fetchone()[0]

    # Total Appointments
    cur.execute("SELECT COUNT(*) FROM appointments")
    appointments = cur.fetchone()[0]

    # Revenue
    cur.execute("SELECT SUM(amount) FROM billing")
    revenue = cur.fetchone()[0]

    return render_template("reports.html",
                           patients=patients,
                           doctors=doctors,
                           appointments=appointments,
                           revenue=revenue)

@app.route('/edit_doctor/<doctor_id>')
def edit_doctor(doctor_id):
    cur = mysql.connection.cursor()
    # Current doctor info
    cur.execute("SELECT * FROM doctors WHERE doctor_id=%s", (doctor_id,))
    doctor = cur.fetchone()
    
    # All doctor IDs and names for dropdown
    cur.execute("SELECT doctor_id, name FROM doctors")
    all_doctors = cur.fetchall()  # [('D001', 'Dr. John Smith'), ('D002', 'Dr. Alice Brown'), ...]
    cur.close()
    
    return render_template("edit_doctor.html", doctor=doctor, all_doctors=all_doctors)

@app.route('/update_doctor', methods=['POST'])
def update_doctor():

    cur = mysql.connection.cursor()   # ✅ ADD THIS LINE (VERY IMPORTANT)

    doctor_id = request.form['doctor_id']
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    username = request.form['username']
    password = request.form['password']
    specialization = request.form['specialization']
    shift_start_hm = request.form['shift_start_hm']
    shift_end_hm = request.form['shift_end_hm']
    shift_type = request.form['shift_type']
    profile_pic = request.files['profile_pic'] 

    

    if profile_pic and profile_pic.filename != "":
        from werkzeug.utils import secure_filename
        import os   # ✅ make sure this is imported

        filename = f"{doctor_id}.png"
        filepath = os.path.join('static/uploads', filename)

        profile_pic.save(filepath)

        cur.execute("""
            UPDATE doctors 
            SET name=%s,
                email=%s,
                phone=%s,
                username=%s,
                password=%s,
                specialization=%s,
                shift_start_hm=%s,
                shift_end_hm=%s,
                shift_type=%s,
                profile_pic=%s
            WHERE doctor_id=%s
        """, (name, email, phone, username, password,
              specialization, shift_start_hm, shift_end_hm,
              shift_type, filename, doctor_id))

    else:
        cur.execute("""
            UPDATE doctors 
            SET name=%s,
                email=%s,
                phone=%s,
                username=%s,
                password=%s,
                specialization=%s,
                shift_start_hm=%s,
                shift_end_hm=%s,
                shift_type=%s
            WHERE doctor_id=%s
        """, (name, email, phone, username, password,
              specialization, shift_start_hm, shift_end_hm,
              shift_type, doctor_id))

    mysql.connection.commit()
    cur.close()

    return redirect('/manage_doctors')

# View all patients
@app.route('/manage_patients')
def view_patients():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM patients")
    patients = cur.fetchall()  # list of tuples
    cur.close()
    return render_template("manage_patients.html", patients=patients)

# Edit patient form
@app.route('/edit_patients', methods=['GET', 'POST'])
def edit_patient():
    cur = mysql.connection.cursor()
    
    # Get all patients for dropdown
    cur.execute("SELECT patient_id, name FROM patients")
    patients = cur.fetchall()  # list of tuples [(patient_id, name), ...]
    
    if request.method == 'POST':
        # Get selected patient ID from dropdown
        patient_id = request.form['patient_id']
        
        # Fetch patient details
        cur.execute("SELECT * FROM patients WHERE patient_id=%s", (patient_id,))
        patient = cur.fetchone()  # tuple: (patient_id, name, age, phone, place, gender, password)
        
        return render_template("edit_patient.html", patients=patients, selected_patient=patient)
    
    return render_template("edit_patients.html", patients=patients)

# Update patient
@app.route('/update_patient', methods=['POST'])
def update_patient():
    patient_id = request.form['patient_id']
    name = request.form['name']
    age = request.form['age']
    phone = request.form['phone']
    place = request.form['place']
    gender = request.form['gender']
    email = request.form['email']

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE patients 
        SET name=%s, age=%s, phone=%s, place=%s, gender=%s, email=%s
        WHERE patient_id=%s
    """, (name, age, phone, place, gender, email, patient_id))
    mysql.connection.commit()
    cur.close()
    return redirect('/manage_patients')

# Delete patient
@app.route('/delete_patient/<patient_id>')
def delete_patient(patient_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM patients WHERE patient_id=%s", (patient_id,))
    mysql.connection.commit()
    cur.close()

    
    return redirect('/manage_patients')

# =========================
# DOCTOR LOGIN
# Doctor ID or Username + Password
# =========================
# =========================
# DOCTOR LOGIN (same style as admin login)
# =========================
# ---------------- DOCTOR LOGIN ----------------
@app.route('/doctor_login', methods=['POST'])
def doctor_login():

    login_id = request.form['username']
    password = request.form['password']

    # text captcha input
    captcha = request.form['captcha'].strip().upper()

    # compare text captcha
    if captcha != session.get('doctor_captcha', ''):
        return render_template(
            "login.html",
            doctor_error="Wrong Captcha"
        )

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT * FROM doctors
        WHERE (username=%s OR doctor_id=%s)
        AND password=%s
        AND status='Active'
    """, (login_id, login_id, password))

    doctor = cur.fetchone()

    if doctor:
        session['doctor_id'] = doctor[0]
        session['doctor_name'] = doctor[1]
        session['doctor_status'] = doctor[7]

        return redirect('/doctor_dashboard')

    return render_template(
        "login.html",
        doctor_error="Invalid Login"
    )

import random
import smtplib
import requests
from flask import render_template, request, session

# =========================
# DOCTOR FORGOT PASSWORD
# =========================
@app.route('/doctor_forgot_password', methods=['GET', 'POST'])
def doctor_forgot_password():

    doctor_id = ''
    method = ''
    phone = ''
    email = ''
    show_otp = False
    msg = ''

    if request.method == 'POST':

        doctor_id = request.form.get('doctor_id', '').strip()
        method = request.form.get('method', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()

        cur = mysql.connection.cursor()

        # =========================
        # SEND OTP
        # =========================
        if 'send_otp' in request.form:

            # PHONE OTP
            if method == 'phone':

                cur.execute("""
                    SELECT * FROM doctors
                    WHERE doctor_id=%s AND phone=%s
                """, (doctor_id, phone))

                user = cur.fetchone()

                if user:

                    otp = str(random.randint(100000, 999999))

                    session['doctor_reset_otp'] = otp
                    session['doctor_reset_id'] = doctor_id

                    # SMS (Fast2SMS)
                    url = "https://www.fast2sms.com/dev/bulkV2"

                    payload = {
                        "variables_values": otp,
                        "route": "otp",
                        "numbers": phone
                    }

                    headers = {
                        "authorization": "YOUR_FAST2SMS_API_KEY"
                    }

                    requests.post(url, data=payload, headers=headers)

                    show_otp = True
                    msg = "OTP Sent To Doctor Mobile"

                else:
                    msg = "Doctor Phone Not Found"

            # EMAIL OTP
            elif method == 'mail':

                cur.execute("""
                    SELECT * FROM doctors
                    WHERE doctor_id=%s AND email=%s
                """, (doctor_id, email))

                user = cur.fetchone()

                if user:

                    otp = str(random.randint(100000, 999999))

                    session['doctor_reset_otp'] = otp
                    session['doctor_reset_id'] = doctor_id

                    sender = "healcarehms@gmail.com"
                    password = "vjrdrfhxbundinen"

                    message = f"""Subject: Doctor HMS OTP

Your OTP is: {otp}
Do not share this OTP.
"""

                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(sender, password)
                    server.sendmail(sender, email, message)
                    server.quit()

                    show_otp = True
                    msg = "OTP Sent To Doctor Email"

                else:
                    msg = "Doctor Email Not Found"

        # =========================
        # UPDATE PASSWORD
        # =========================
        elif 'update_password' in request.form:

            otp = request.form.get('otp', '').strip()
            new_password = request.form.get('new_password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()

            if otp != session.get('doctor_reset_otp'):
                msg = "Wrong OTP"

            elif new_password != confirm_password:
                msg = "Password Not Match"

            else:

                cur.execute("""
                    UPDATE doctors
                    SET password=%s
                    WHERE doctor_id=%s
                """, (new_password, session['doctor_reset_id']))

                mysql.connection.commit()
                cur.close()

                session.pop('doctor_reset_otp', None)
                session.pop('doctor_reset_id', None)

                return '''
                <script>
                alert("Doctor Password Updated Successfully");
                window.location='/';
                </script>
                '''

    return render_template(
        'doctor_forgot_password.html',
        doctor_id=doctor_id,
        method=method,
        phone=phone,
        email=email,
        show_otp=show_otp,
        msg=msg
    )

from flask import Flask, render_template, session, send_file, request, redirect
import random, string, io

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------------- HOME ----------------
@app.route('/')
def index():
    return render_template("login.html")


# ---------------- CAPTCHA IMAGE ----------------
# Replace your /captcha route with this

@app.route('/captcha')
def captcha():

    import random, string, io
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    session['doctor_captcha'] = text

    # Bigger image
    img = Image.new('RGB', (220, 80), (255,255,255))
    draw = ImageDraw.Draw(img)

    # Bigger font
    try:
        font = ImageFont.truetype("arial.ttf", 42)
    except:
        font = ImageFont.load_default()

    # Noise lines
    for i in range(10):
        draw.line(
            (
                random.randint(0,220),
                random.randint(0,80),
                random.randint(0,220),
                random.randint(0,80)
            ),
            fill=(160,160,160),
            width=1
        )

    # Draw each letter bigger
    x = 15
    for ch in text:
        y = random.randint(10,25)

        draw.text(
            (x, y),
            ch,
            font=font,
            fill=(
                random.randint(0,100),
                random.randint(0,100),
                random.randint(0,255)
            )
        )
        x += 38

    # Dots
    for i in range(150):
        draw.point(
            (random.randint(0,220), random.randint(0,80)),
            fill=(0,0,0)
        )

    img = img.filter(ImageFilter.SMOOTH)

    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)

    return send_file(buffer, mimetype='image/png')

@app.route('/delete_doctor/<doctor_id>')
def delete_doctor(doctor_id):

    if 'admin' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM doctors WHERE doctor_id=%s", (doctor_id,))

    mysql.connection.commit()
    cur.close()

    return redirect('/manage_doctors')

@app.route('/approve/<token>')
def approve(token):

    cur = mysql.connection.cursor()

    cur.execute("""
    UPDATE appointments 
    SET status='Approved'
    WHERE appointment_token=%s
    """,(token,))

    mysql.connection.commit()

    return redirect('/view_appointments')


@app.route('/reject/<token>')
def reject(token):

    cur = mysql.connection.cursor()

    cur.execute("""
    UPDATE appointments 
    SET status='Rejected'
    WHERE appointment_token=%s
    """,(token,))

    mysql.connection.commit()

    return redirect('/view_appointments')

# DOCTOR DASHBOARD
@app.route('/doctor_dashboard')
def doctor_dashboard():

    # ✅ Correct session check
    if 'doctor_id' not in session:
        return redirect('/')

    doctor_id = session['doctor_id']
    doctor_name = session.get('doctor_name')

    cur = mysql.connection.cursor()

    # Profile Image
    cur.execute(
        "SELECT profile_pic FROM doctors WHERE doctor_id=%s",
        (doctor_id,)
    )
    row = cur.fetchone()
    profile_image = row[0] if row else "default.png"

    # Total Patients
    cur.execute("""
        SELECT COUNT(DISTINCT patient_id)
        FROM appointments
        WHERE doctor_id=%s
    """, (doctor_id,))
    total_patients = cur.fetchone()[0]

    # Total Appointments
    cur.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE doctor_id=%s
    """, (doctor_id,))
    total_appointments = cur.fetchone()[0]

    # Today Appointments
    cur.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE doctor_id=%s
        AND appointment_date = CURDATE()
    """, (doctor_id,))
    today_appointments = cur.fetchone()[0]

    # Pending
    cur.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE doctor_id=%s
        AND status='Pending'
    """, (doctor_id,))
    pending = cur.fetchone()[0]

    # Notifications
    notifications = []

    if pending > 0:
        notifications.append({
            "text": f"{pending} pending approvals",
            "link": "/doctor_appointments"
        })

    if today_appointments > 0:
        notifications.append({
            "text": f"{today_appointments} appointments today",
            "link": "/doctor_appointments"
        })

    if len(notifications) == 0:
        notifications.append({
            "text": "No new notifications",
            "link": "#"
        })

    cur.close()

    return render_template(
        "doctor_dashboard.html",
        doctor_name=doctor_name,
        total_patients=total_patients,
        total_appointments=total_appointments,
        today_appointments=today_appointments,
        pending=pending,
        notifications=notifications,
        profile_image=profile_image
    )


@app.route('/doctor_patients')
def doctor_patients():

    if 'doctor_id' not in session:
        return redirect('/')

    doctor_id = session['doctor_id']

    cur = mysql.connection.cursor()

    cur.execute("""
    SELECT DISTINCT p.patient_id,
           p.name,
           p.age,
           p.phone,
           p.place
    FROM patients p
    JOIN appointments a
    ON p.patient_id = a.patient_id
    WHERE a.doctor_id=%s
    """,(doctor_id,))

    patients = cur.fetchall()

    cur.close()

    return render_template("doctor_patients.html", patients=patients)

@app.route('/doctor_calendar')
def doctor_calendar():

    if 'doctor_id' not in session:
        return redirect('/')

    doctor_id = session['doctor_id']

    import calendar
    from datetime import datetime

    today = datetime.now()
    month = int(request.args.get('month', today.month))
    year = int(request.args.get('year', today.year))

    # ⬅️➡️ Month navigation logic
    prev_month = month - 1
    next_month = month + 1
    prev_year = year
    next_year = year

    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    if next_month == 13:
        next_month = 1
        next_year += 1

    cal = calendar.monthcalendar(year, month)

    cur = mysql.connection.cursor()

 # ✅ Pending
    cur.execute("""
SELECT DAY(appointment_date), COUNT(*)
FROM appointments
WHERE doctor_id=%s AND status='Pending'
AND MONTH(appointment_date)=%s AND YEAR(appointment_date)=%s
GROUP BY DAY(appointment_date)
""",(doctor_id, month, year))
    pending_data = {int(k): int(v) for k,v in cur.fetchall()}

# ✅ Approved
    cur.execute("""
SELECT DAY(appointment_date), COUNT(*)
FROM appointments
WHERE doctor_id=%s AND status='Approved'
AND MONTH(appointment_date)=%s AND YEAR(appointment_date)=%s
GROUP BY DAY(appointment_date)
""",(doctor_id, month, year))
    accepted_data = {int(k): int(v) for k,v in cur.fetchall()}

# ✅ Finished
    cur.execute("""
SELECT DAY(appointment_date), COUNT(*)
FROM appointments
WHERE doctor_id=%s AND status='Finished'
AND MONTH(appointment_date)=%s AND YEAR(appointment_date)=%s
GROUP BY DAY(appointment_date)
""",(doctor_id, month, year))
    finished_data = {int(k): int(v) for k,v in cur.fetchall()}

# ✅ Cancelled
    cur.execute("""
SELECT DAY(appointment_date), COUNT(*)
FROM appointments
WHERE doctor_id=%s AND status='Canceled'
AND MONTH(appointment_date)=%s AND YEAR(appointment_date)=%s
GROUP BY DAY(appointment_date)
""",(doctor_id, month, year))
    cancelled_data = {int(k): int(v) for k,v in cur.fetchall()}


    cancelled_data = dict(cur.fetchall())
    # 🔍 Selected date
    selected_date = request.args.get('date')
    appointments = []

    if selected_date:
        cur.execute("""
        SELECT token,name,appointment_date,
               appointment_time,problem,status
        FROM appointments
        WHERE doctor_id=%s AND appointment_date=%s
        """,(doctor_id, selected_date))

        appointments = cur.fetchall()

    cur.close()

    return render_template(
        "doctor_calendar.html",
        calendar=cal,
        pending_data=pending_data,
        month=month,
        year=year,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year,
        appointments=appointments,
        finished_data=finished_data,
      accepted_data=accepted_data,
      cancelled_data=cancelled_data,
        selected_date=selected_date
    )




@app.route('/view_doctor/<int:doctor_id>')
def view_doctor(doctor_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM doctors WHERE doctor_id=%s", (doctor_id,))
    doctor = cur.fetchone()

    if not doctor:
        return "Doctor not found"

    return render_template("view_doctor.html", doctor=doctor)

@app.route('/doctor_profile')
def doctor_profile():

    if 'doctor_id' not in session:
        return redirect('/')

    doctor_id = session['doctor_id']

    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM doctors WHERE doctor_id=%s",(doctor_id,))
    doctor = cur.fetchone()

    cur.close()

    return render_template("doctor_profile.html", doctor=doctor)

@app.route('/update_doctor_profile', methods=['POST'])
def update_doctor_profile():

    # ✅ correct session check
    if 'doctor_id' not in session:
        return redirect('/')

    doctor_id = session['doctor_id']

    name = request.form['name']
    phone = request.form['phone']
    email = request.form['email']
    password = request.form['password']

    file = request.files.get('profile_pic')

    cur = mysql.connection.cursor()

    from werkzeug.utils import secure_filename
    import os

    if file and file.filename != "":
        filename = secure_filename(f"{doctor_id}.png")
        filepath = os.path.join("static/uploads", filename)
        file.save(filepath)

        cur.execute("""
            UPDATE doctors
            SET name=%s, phone=%s, email=%s, password=%s, profile_pic=%s
            WHERE doctor_id=%s
        """, (name, phone, email, password, filename, doctor_id))

    else:
        cur.execute("""
            UPDATE doctors
            SET name=%s, phone=%s, email=%s, password=%s
            WHERE doctor_id=%s
        """, (name, phone, email, password, doctor_id))

    mysql.connection.commit()
    cur.close()

    return redirect('/doctor_profile')

# ---------------- PATIENT LOGIN ----------------
@app.route('/patient_login', methods=['POST'])
def patient_login():

    patient_id = request.form['patient_id']
    password   = request.form['password']
    captcha    = request.form['patient_captcha'].strip().upper()

    # captcha check
    if captcha != session.get('doctor_captcha', ''):
        return render_template(
            "login.html",
            patient_error="Wrong Captcha"
        )

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT * FROM patients
        WHERE patient_id=%s
        AND password=%s
        AND status='Active'
    """, (patient_id, password))

    account = cur.fetchone()

    if account:
        session['patient_id'] = patient_id
        return redirect('/patient_dashboard')

    return render_template(
        "login.html",
        patient_error="Incorrect Patient ID or Password"
    )


from flask import Flask, render_template, request, session
import random
import smtplib
from twilio.rest import Client

import random
import smtplib
import requests
from flask import render_template, request, session

# =========================
# FORGOT PASSWORD
# =========================
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():

    patient_id = ''
    method = ''
    phone = ''
    email = ''
    show_otp = False
    msg = ''

    if request.method == 'POST':

        patient_id = request.form.get('patient_id', '').strip()
        method = request.form.get('method', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()

        cur = mysql.connection.cursor()

        # =========================
        # SEND OTP
        # =========================
        if 'send_otp' in request.form:

            # =========================
            # PHONE OTP (SMS FIXED)
            # =========================
            if method == 'phone':

                cur.execute("""
                    SELECT * FROM patients
                    WHERE patient_id=%s AND phone=%s
                """, (patient_id, phone))

                user = cur.fetchone()

                if user:

                    otp = str(random.randint(100000, 999999))

                    session['reset_otp'] = otp
                    session['reset_patient'] = patient_id

                    # =========================
                    # SEND SMS VIA FAST2SMS
                    # =========================
                    url = "https://www.fast2sms.com/dev/bulkV2"

                    payload = {
                        "variables_values": otp,
                        "route": "otp",
                        "numbers": phone
                    }

                    headers = {
                        "authorization": "YOUR_FAST2SMS_API_KEY"
                    }

                    response = requests.post(url, data=payload, headers=headers)

                    print("SMS RESPONSE:", response.text)

                    show_otp = True
                    msg = "OTP Sent To Registered Mobile Number"

                else:
                    msg = "Phone Number Not Registered"

            # =========================
            # EMAIL OTP
            # =========================
            elif method == 'mail':

                cur.execute("""
                    SELECT * FROM patients
                    WHERE patient_id=%s AND email=%s
                """, (patient_id, email))

                user = cur.fetchone()

                if user:

                    otp = str(random.randint(100000, 999999))

                    session['reset_otp'] = otp
                    session['reset_patient'] = patient_id

                    sender = "healcarehms@gmail.com"
                    password = "vjrdrfhxbundinen"

                    message = f"""Subject: HealCare HMS OTP

Your OTP is: {otp}
Do not share this OTP with anyone.
"""

                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(sender, password)
                    server.sendmail(sender, email, message)
                    server.quit()

                    show_otp = True
                    msg = "OTP Sent To Registered Email"

                else:
                    msg = "Email Not Registered"

        # =========================
        # UPDATE PASSWORD
        # =========================
        elif 'update_password' in request.form:

            otp = request.form.get('otp', '').strip()
            new_password = request.form.get('new_password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()

            if otp != session.get('reset_otp'):
                msg = "Wrong OTP"

            elif new_password != confirm_password:
                msg = "Password Not Match"

            else:

                cur.execute("""
                    UPDATE patients
                    SET password=%s
                    WHERE patient_id=%s
                """, (new_password, session['reset_patient']))

                mysql.connection.commit()
                cur.close()

                session.pop('reset_otp', None)
                session.pop('reset_patient', None)

                return '''
                <script>
                alert("Password Updated Successfully");
                window.location='/';
                </script>
                '''

    return render_template(
        'forgot_password.html',
        patient_id=patient_id,
        method=method,
        phone=phone,
        email=email,
        show_otp=show_otp,
        msg=msg
    )
# LIVE CHECK
# =========================
@app.route('/check_reset_user', methods=['POST'])
def check_reset_user():

    patient_id = request.form.get('patient_id', '').strip()
    method = request.form.get('method', '').strip()
    value = request.form.get('value', '').strip()

    cur = mysql.connection.cursor()

    if method == 'phone':

        cur.execute("""
        SELECT * FROM patients
        WHERE patient_id=%s AND phone=%s
        """,(patient_id,value))

    else:

        cur.execute("""
        SELECT * FROM patients
        WHERE patient_id=%s AND email=%s
        """,(patient_id,value))

    user = cur.fetchone()
    cur.close()

    if user:
        return "Valid Registered Details"
    else:
        return "Wrong / Not Registered"


# =========================
# LIVE OTP VERIFY
# =========================
@app.route('/verify_live_otp', methods=['POST'])
def verify_live_otp():

    otp = request.form.get('otp', '').strip()

    if otp == session.get('reset_otp'):
        return "OTP Correct"
    else:
        return "Wrong OTP"
    


# Patient Register Page
import re
import random
from flask import render_template, request
from flask_mail import Message

@app.route('/patient_register', methods=['GET', 'POST'])
def patient_register():

    import re
    import random

    if request.method == 'POST':

        name = request.form['name']
        age = request.form['age']
        phone = request.form['phone']
        place = request.form['place']
        gender = request.form['gender']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # ================= PASSWORD MATCH =================
        if password != confirm_password:
            return """
            <script>
            alert('Password and Confirm Password do not match');
            window.history.back();
            </script>
            """

        # ================= PASSWORD RULE =================
        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$'

        if not re.match(pattern, password):
            return """
            <script>
            alert('Password must contain minimum 8 characters, uppercase, lowercase, number and special character');
            window.history.back();
            </script>
            """

        cur = mysql.connection.cursor()

        # ================= EMAIL EXISTS =================
        cur.execute("SELECT * FROM patients WHERE email=%s", (email,))
        already = cur.fetchone()

        if already:
            cur.close()
            return """
            <script>
            alert('Email already registered');
            window.history.back();
            </script>
            """

        # ================= UNIQUE ID =================
        while True:
            patient_id = "PAT" + str(random.randint(1000, 9999))
            cur.execute("SELECT * FROM patients WHERE patient_id=%s", (patient_id,))
            check = cur.fetchone()

            if not check:
                break

        # ================= INSERT =================
        cur.execute("""
        INSERT INTO patients
        (patient_id,name,age,phone,place,gender,email,password)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
        """, (patient_id, name, age, phone, place, gender, email, password))

        mysql.connection.commit()
        cur.close()

        # ================= PROFESSIONAL MAIL =================
        html_body = f"""
        <html>
        <body style="margin:0;padding:0;background:#f4f8fb;font-family:Arial,sans-serif;">

        <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
        <td align="center">

        <table width="650" cellpadding="0" cellspacing="0" 
        style="background:#ffffff;margin-top:30px;border-radius:12px;
        overflow:hidden;box-shadow:0 0 15px rgba(0,0,0,0.08);">

            <!-- Header -->
            <tr>
                <td style="background:#0d6efd;padding:25px;text-align:center;color:white;">
                    <img src="https://cdn-icons-png.flaticon.com/512/2967/2967350.png"
                    width="70"><br>
                    <h1 style="margin:10px 0 0 0;">Heal Care Hospital</h1>
                    <p style="margin:5px 0 0 0;">Patient Registration Successful</p>
                </td>
            </tr>

            <!-- Welcome -->
            <tr>
                <td style="padding:30px;">
                    <h2 style="color:#0d6efd;">Hello {name},</h2>
                    <p style="font-size:16px;color:#444;line-height:28px;">
                    Thank you for registering with <b>Heal Care Hospital</b>.
                    Your patient account has been created successfully.
                    </p>

                    <table width="100%" cellpadding="10" cellspacing="0"
                    style="border:1px solid #ddd;border-radius:10px;margin-top:20px;">
                        <tr style="background:#f8f9fa;">
                            <td colspan="2"><b>Patient Details</b></td>
                        </tr>

                        <tr>
                            <td><b>Patient ID</b></td>
                            <td>{patient_id}</td>
                        </tr>

                        <tr>
                            <td><b>Name</b></td>
                            <td>{name}</td>
                        </tr>

                        <tr>
                            <td><b>Age</b></td>
                            <td>{age}</td>
                        </tr>

                        <tr>
                            <td><b>Phone</b></td>
                            <td>{phone}</td>
                        </tr>

                        <tr>
                            <td><b>Place</b></td>
                            <td>{place}</td>
                        </tr>

                        <tr>
                            <td><b>Gender</b></td>
                            <td>{gender}</td>
                        </tr>

                        <tr>
                            <td><b>Email</b></td>
                            <td>{email}</td>
                        </tr>

                        <tr>
                            <td><b>Password</b></td>
                            <td>{password}</td>
                        </tr>
                    </table>

                    <!-- Login Button -->
                    <div style="text-align:center;margin-top:35px;">
                        <a href="http://127.0.0.1:5000/"
                        style="background:#0d6efd;color:white;
                        padding:14px 28px;
                        text-decoration:none;
                        border-radius:8px;
                        font-size:16px;">
                        Login Now
                        </a>
                    </div>

                    <p style="margin-top:30px;color:#666;font-size:14px;">
                    Keep this email safe for future login reference.
                    </p>
                </td>
            </tr>

            <!-- Footer -->
            <tr>
                <td style="background:#f1f5f9;padding:18px;text-align:center;
                font-size:13px;color:#666;">
                    © 2026 Heal Care Hospital <br>
                    Caring for Life, Every Moment.
                </td>
            </tr>

        </table>

        </td>
        </tr>
        </table>

        </body>
        </html>
        """

        msg = Message(
            subject="Welcome to Heal Care Hospital",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )

        msg.html = html_body
        mail.send(msg)

        return f"""
        <script>
        alert('Registration Successful! Your Patient ID is: {patient_id}');
        window.location.href='/';
        </script>
        """

    return render_template("patient_register.html")

    # Patient Dashboard
@app.route('/patient_dashboard')
def patient_dashboard():
    if 'patient_id' not in session:
        return redirect('/')

    patient_id = session['patient_id']
    cur = mysql.connection.cursor()

    # Patient details
    cur.execute("SELECT * FROM patients WHERE patient_id=%s", (patient_id,))
    patient = cur.fetchone()

    # Dashboard cards
    cur.execute("SELECT COUNT(*) FROM appointments WHERE patient_id=%s", (patient_id,))
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments WHERE patient_id=%s AND status='Pending'", (patient_id,))
    pending = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments WHERE patient_id=%s AND status='Approved'", (patient_id,))
    approved = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM appointments 
        WHERE patient_id=%s AND appointment_date >= CURDATE()
    """, (patient_id,))
    upcoming = cur.fetchone()[0]

    cur.close()

    return render_template(
        "patient_dashboard.html",
        patient=patient,
        total=total,
        pending=pending,
        approved=approved,
        upcoming=upcoming
    )
    
    
    return redirect('/patient_dashboard')

# Change Password
@app.route('/change_patient_password', methods=['POST'])
def change_patient_password():
    if 'patient_id' not in session:
        return redirect('/')
    
    patient_id = session['patient_id']
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT password FROM patients WHERE patient_id=%s", (patient_id,))
    actual_password = cur.fetchone()[0]
    
    if current_password != actual_password:
        flash("Current password is incorrect.", "error")
        return redirect('/patient_dashboard')
    
    if new_password != confirm_password:
        flash("New password and confirm password do not match.", "error")
        return redirect('/patient_dashboard')
    
    # Optional strong password validation
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$'
    if not re.match(pattern, new_password):
        flash("Password must be at least 8 characters and include uppercase, lowercase, number, and special character.", "error")
        return redirect('/patient_dashboard')
    
    cur.execute("UPDATE patients SET password=%s WHERE patient_id=%s", (new_password, patient_id))
    mysql.connection.commit()
    cur.close()
    
    flash("Password changed successfully!", "success")
    return redirect('/patient_dashboard')
#------------------------------------------------------------------

# Toggle Doctor Status
@app.route('/toggle_doctor_status/<doctor_id>')
def toggle_doctor_status(doctor_id):
    cur = mysql.connection.cursor()
    # Get current status
    cur.execute("SELECT status FROM doctors WHERE doctor_id=%s", (doctor_id,))
    status = cur.fetchone()[0]

    # Toggle status
    new_status = 'Inactive' if status == 'Active' else 'Active'
    cur.execute("UPDATE doctors SET status=%s WHERE doctor_id=%s", (new_status, doctor_id))
    mysql.connection.commit()
    cur.close()
    return redirect('/manage_doctors')


# Toggle Patient Status
@app.route('/toggle_patient_status/<patient_id>')
def toggle_patient_status(patient_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT status FROM patients WHERE patient_id=%s", (patient_id,))
    status = cur.fetchone()[0]

    new_status = 'Inactive' if status == 'Active' else 'Active'
    cur.execute("UPDATE patients SET status=%s WHERE patient_id=%s", (new_status, patient_id))
    mysql.connection.commit()
    cur.close()
    return redirect('/manage_patients')

@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():

    if 'patient_id' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    # patient data
    cur.execute("SELECT * FROM patients WHERE patient_id=%s", (session['patient_id'],))
    patient = cur.fetchone()

    # departments
    cur.execute("SELECT DISTINCT specialization FROM doctors WHERE status='Active'")
    departments = [d[0] for d in cur.fetchall()]

    if request.method == 'POST':

        appointment_date = request.form.get('appointment_date')

        if not appointment_date:
            flash("❌ Select appointment date")
            return redirect('/book_appointment')

        # date validation
        today = datetime.now().date()
        selected_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()

        if selected_date < today:
            flash("❌ Cannot select past date")
            return redirect('/book_appointment')

        # form data
        name = request.form['name']
        age = request.form['age']
        place = request.form['place']
        email = request.form['email']
        specialization = request.form['department']
        doctor_id = request.form['doctor']
        doctor_name = request.form['doctor_name']
        appointment_time = request.form['appointment_time']
        problem = request.form.get('problem')

        # slot check
        cur.execute("""
            SELECT * FROM appointments
            WHERE doctor_id=%s AND appointment_date=%s AND appointment_time=%s
            AND status IN ('Pending','Approved')
        """, (doctor_id, appointment_date, appointment_time))

        if cur.fetchone():
            flash("❌ Slot already booked")
            return redirect('/book_appointment')

        # token
        token = "APT" + str(random.randint(1000, 9999))

        # INSERT with status = Pending
        cur.execute("""
            INSERT INTO appointments(
                token, name, age, place, email, doctor_name,
                specialization, appointment_date, appointment_time,
                problem, patient_id, doctor_id, status
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            token, name, age, place, email, doctor_name,
            specialization, appointment_date, appointment_time,
            problem, session['patient_id'], doctor_id,
            "Pending"
        ))

        mysql.connection.commit()

        # get appointment id
        appointment_id = cur.lastrowid

        # fetch status
        cur.execute("SELECT status FROM appointments WHERE appointment_id=%s", (appointment_id,))
        status = cur.fetchone()[0]

        # button logic
        if status == "Accepted":
            view_button = f"""
            <div style="text-align:center;margin-top:20px;">
                <a href="http://127.0.0.1:5000/appointment_form/{appointment_id}"
                   style="
                      background:#198754;
                      color:white;
                      padding:12px 18px;
                      text-decoration:none;
                      border-radius:8px;
                      display:inline-block;
                      font-weight:bold;
                   ">
                   View Appointment Slip
                </a>
            </div>
            """
        else:
            view_button = f"""
            <p style="text-align:center;color:red;font-weight:bold;margin-top:15px;">
                Status: {status} (Available after approval)
            </p>
            """

        # EMAIL SEND
        msg = Message(
            subject="🎉 Appointment Booked - Heal Care Hospital",
            recipients=[email]
        )

        msg.html = f"""
        <html>
        <body style="font-family:Arial;background:#f4f8ff;padding:20px;">

        <div style="max-width:520px;margin:auto;background:white;padding:25px;border-radius:12px;box-shadow:0 0 10px #ccc;">

            <h2 style="background:#0d6efd;color:white;padding:12px;text-align:center;border-radius:8px;">
                Appointment Status Update
            </h2>

            <p>Dear <b>{name}</b>,</p>

            <p style="color:green;"><b>Token: {token}</b></p>

            <p>👨‍⚕️ Doctor: {doctor_name}</p>
            <p>🏥 Department: {specialization}</p>
            <p>📅 Date: {appointment_date}</p>
            <p>⏰ Time: {appointment_time}</p>

            <hr>

            <p><b>Status:</b> {status}</p>

            {view_button}

            <p style="font-size:12px;color:gray;text-align:center;margin-top:20px;">
                Heal Care Hospital
            </p>

        </div>

        </body>
        </html>
        """

        mail.send(msg)

        flash("Appointment booked successfully!")
        return redirect('/my_appointments')

    return render_template(
        "book_appointment.html",
        patient=patient,
        departments=departments
    )

@app.route('/appointment_report', methods=['GET','POST'])
def appointment_report():

    cur = mysql.connection.cursor()

    # Get doctors for dropdown
    cur.execute("SELECT doctor_id, name FROM doctors")
    doctors = cur.fetchall()

    # Get departments
    cur.execute("SELECT DISTINCT specialization FROM doctors")
    departments = [d[0] for d in cur.fetchall()]

    appointments = []

    if request.method == "POST":

        from_date = request.form.get("from_date")
        to_date = request.form.get("to_date")
        doctor_id = request.form.get("doctor_id")
        department = request.form.get("department")
        status = request.form.get("status")

        query = """
        SELECT token,name,doctor_name,specialization,
               appointment_date,appointment_time,status
        FROM appointments
        WHERE 1=1
        """

        params = []

        if from_date and to_date:
            query += " AND appointment_date BETWEEN %s AND %s"
            params.append(from_date)
            params.append(to_date)

        if doctor_id:
            query += " AND doctor_id=%s"
            params.append(doctor_id)

        if department:
            query += " AND specialization=%s"
            params.append(department)

        if status:
            query += " AND status=%s"
            params.append(status)

        query += " ORDER BY appointment_date DESC"

        cur.execute(query, tuple(params))
        appointments = cur.fetchall()

    cur.close()

    return render_template(
        "appointment_report.html",
        doctors=doctors,
        departments=departments,
        appointments=appointments
    )


@app.route('/patient_report', methods=['GET','POST'])
def patient_report():

    cur = mysql.connection.cursor()

    # Get all patients for dropdown
    cur.execute("SELECT patient_id, name FROM patients")
    patients = cur.fetchall()

    report = []

    if request.method == 'POST':

        patient_id = request.form['patient_id']

        cur.execute("""
        SELECT token,
               doctor_name,
               specialization,
               appointment_date,
               appointment_time,
               problem,
               status
        FROM appointments
        WHERE patient_id=%s
        ORDER BY appointment_date DESC
        """,(patient_id,))

        report = cur.fetchall()

    cur.close()

    return render_template(
        "patient_report.html",
        patients=patients,
        report=report
    )
#-------------------------------------------------------------------------
@app.route('/send_report/<patient_id>', methods=['GET','POST'])
def send_report(patient_id):

    cur = mysql.connection.cursor()

    if request.method == "POST":

        doctor_name = request.form['doctor_name']
        department = request.form['department']
        report_text = request.form['report_text']

        cur.execute("""
        INSERT INTO patient_reports
        (patient_id,doctor_name,department,report_text,report_date)
        VALUES(%s,%s,%s,%s,CURDATE())
        """,(patient_id,doctor_name,department,report_text))

        mysql.connection.commit()

        flash("Report sent to patient successfully!")

        return redirect('/manage_patients')

    return render_template("send_report.html", patient_id=patient_id)

#---------------------------------------------------------------------------


@app.route('/appointment_slip/<token>')
def appointment_slip(token):

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT * FROM appointments WHERE token=%s",
        (token,)
    )

    appointment = cur.fetchone()

    qr = "qr/" + str(token) + ".png"

    return render_template(
        "appointment_slip.html",
        appointment=appointment,
        qr=qr
    )

@app.route('/appointment_form/<int:appointment_id>')
def appointment_form(appointment_id):

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT token,name,age,place,doctor_name,
               specialization,appointment_date,
               appointment_time,problem,status
        FROM appointments
        WHERE appointment_id=%s
    """, (appointment_id,))

    appointment = cur.fetchone()

    if not appointment:
        return "Invalid appointment"

    token = appointment[0]

    import qrcode
    import os

    os.makedirs("static/qrcodes", exist_ok=True)

    qr_path = f"static/qrcodes/{token}.png"

    if not os.path.exists(qr_path):
        img = qrcode.make(token)
        img.save(qr_path)

    cur.close()

    return render_template(
        "appointment_form.html",
        appointment=appointment,
        qr=qr_path
    )




from reportlab.pdfgen import canvas

@app.route('/download_pdf/<token>')
def download_pdf(token):

    cur = mysql.connection.cursor()

    cur.execute("""
    SELECT token,name,doctor_name,
           specialization,appointment_date,
           appointment_time
    FROM appointments
    WHERE token=%s
    """,(token,))

    a = cur.fetchone()

    filename = "appointment_"+token+".pdf"
    filepath = "static/" + filename

    c = canvas.Canvas(filepath)

    c.drawString(200,800,"City Hospital Appointment Slip")

    c.drawString(100,750,"Token : "+a[0])
    c.drawString(100,720,"Patient : "+a[1])
    c.drawString(100,690,"Doctor : "+a[2])
    c.drawString(100,660,"Department : "+a[3])
    c.drawString(100,630,"Date : "+str(a[4]))
    c.drawString(100,600,"Time : "+a[5])

    c.save()

    return redirect("/"+filepath)


import os
import qrcode

@app.route('/generate_qr/<token>')
def generate_qr(token):

    folder = "static/qrcodes"

    # Create folder if it doesn't exist
    if not os.path.exists(folder):
        os.makedirs(folder)

    path = os.path.join(folder, token + ".png")

    img = qrcode.make(token)
    img.save(path)

    return path


from datetime import datetime

@app.route('/get_doctors/<department>')
def get_doctors(department):
    cur = mysql.connection.cursor()

    cur.execute("SELECT doctor_id, name FROM doctors WHERE specialization=%s AND status='active'", (department,))
    doctors = cur.fetchall()

    doctor_list = []
    for d in doctors:
        doctor_list.append({
            "id": d[0],
            "name": d[1]
        })

    return jsonify({"doctors": doctor_list})


@app.route('/my_appointments')
def my_appointments():
    if 'patient_id' not in session:
        return redirect('/')

    patient_id = session['patient_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT appointment_id, token, doctor_name, specialization,
appointment_date, appointment_time, problem,
status, cancel_reason, canceled_by
FROM appointments
WHERE patient_id=%s
        ORDER BY appointment_date DESC
    """, (patient_id,))
    appointments = cur.fetchall()
    cur.close()
    return render_template('my_appointments.html', appointments=appointments)

@app.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):

    reason = request.form['reason']

    cur = mysql.connection.cursor()

    cur.execute("""
    UPDATE appointments
    SET status='Canceled',
        cancel_reason=%s,
        canceled_by='Patient'
    WHERE appointment_id=%s
    """,(reason,appointment_id))

    mysql.connection.commit()
    cur.close()

    flash("Appointment canceled successfully!", "success")
    return redirect('/my_appointments')

from datetime import date
today = date.today()
@app.route('/doctor_appointments')
def doctor_appointments():

    if 'doctor_id' not in session:
        return redirect('/')

    doctor_id = session['doctor_id']

    # 🔍 Filters
    date = request.args.get('date')
    patient_name = request.args.get('name')

    cur = mysql.connection.cursor()

    # ✅ GET PATIENT ID + NAME
    cur.execute("""
    SELECT DISTINCT patient_id, name 
    FROM appointments 
    WHERE doctor_id=%s
     """, (doctor_id,))

    patients = cur.fetchall()   # [(PAT001, John), (PAT002, Ravi)]

    # 🔍 MAIN QUERY
    query = """
        SELECT appointment_id,
               token,
               name,
               age,
               place,
               doctor_name,
               specialization,
               appointment_date,
               appointment_time,
               problem,
               status,
               cancel_reason,
               canceled_by
        FROM appointments
        WHERE doctor_id=%s
    """

    params = [doctor_id]

    if date:
        query += " AND appointment_date=%s"
        params.append(date)

    if patient_name:
        query += " AND name=%s"   # 🔥 exact match for dropdown
        params.append(patient_name)

    query += " ORDER BY appointment_date DESC, appointment_time DESC"

    cur.execute(query, tuple(params))
    appointments = cur.fetchall()

    # ✅ Today count
    cur.execute("""
        SELECT COUNT(*) FROM appointments
        WHERE doctor_id=%s AND appointment_date=CURDATE()
    """, (doctor_id,))
    today_count = cur.fetchone()[0]

    cur.close()

    return render_template(
    "doctor_appointments.html",
    appointments=appointments,
    today_count=today_count,
    patients=patients,
    today=today   # 🔥 ADD THIS
)
@app.route('/doctor_cancel/<int:id>', methods=['POST'])
def doctor_cancel(id):

    if 'doctor_id' not in session:
        return redirect('/')

    doctor_id = session['doctor_id']
    doctor_name = session.get('doctor_name', 'Doctor')

    reason = request.form['reason']

    cur = mysql.connection.cursor()

    # ✅ Update cancel status
    cur.execute("""
        UPDATE appointments
        SET status='Canceled',
            cancel_reason=%s,
            canceled_by=%s
        WHERE appointment_id=%s
        AND doctor_id=%s
    """, (reason, doctor_name, id, doctor_id))

    mysql.connection.commit()

    # ✅ Get patient details
    cur.execute("""
        SELECT email, name, appointment_id
        FROM appointments
        WHERE appointment_id=%s
    """, (id,))

    data = cur.fetchone()
    cur.close()

    if data:
        patient_email = data[0]
        patient_name = data[1]
        appointment_id = data[2]

        # ================= REJECTION EMAIL LINK =================
        

        # ================= PROFESSIONAL REJECTION EMAIL =================
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        </head>

        <body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">

        <div style="max-width:600px;margin:20px auto;background:#ffffff;
        border-radius:10px;overflow:hidden;border:1px solid #e6e6e6;">

        <!-- HEADER -->
        <div style="background:#dc3545;color:white;padding:20px;text-align:center;">
            <h2 style="margin:0;">Heal Care Hospital</h2>
            <p style="margin:5px 0 0;font-size:13px;">Appointment Update Notification</p>
        </div>

        <!-- BODY -->
        <div style="padding:25px;">

            <p style="font-size:16px;">Dear <b>{patient_name}</b>,</p>

            <p style="font-size:15px;line-height:1.6;color:#333;">
                We regret to inform you that your appointment request has been 
                <b style="color:red;">NOT APPROVED</b> by the doctor.
            </p>

            <!-- REASON BOX -->
            <div style="background:#fff3cd;padding:15px;border-radius:8px;
            margin:20px 0;border-left:5px solid #ffc107;">
                <p style="margin:0;font-size:14px;">
                    <b>Appointment ID:</b> {appointment_id}<br>
                    <b>Status:</b> Rejected<br>
                    <b>Reason:</b> {reason}
                </p>
            </div>

            <!-- BUTTON -->
            <div style="text-align:center;margin:30px 0;">
                <a href="{view_link}"
                   style="background:#6c757d;color:white;
                   padding:12px 25px;text-decoration:none;
                   border-radius:6px;font-weight:bold;display:inline-block;">
                   View Appointment Details
                </a>
            </div>

            <p style="font-size:13px;color:#666;line-height:1.5;">
                You may rebook another appointment or contact our hospital reception for assistance.  
                We sincerely apologize for the inconvenience caused.
            </p>

        </div>

        <!-- FOOTER -->
        <div style="background:#f1f1f1;text-align:center;
        padding:12px;font-size:12px;color:#666;">
            © 2026 Heal Care Hospital | All Rights Reserved
        </div>

        </div>

        </body>
        </html>
        """

        # ================= SEND EMAIL =================
        msg = Message(
            subject="❌ Appointment Not Approved - Heal Care Hospital",
            sender=app.config['MAIL_USERNAME'],
            recipients=[patient_email]
        )

        msg.html = html_body
        mail.send(msg)

    return redirect('/doctor_appointments')

@app.route('/admin_accept/<int:id>')
def admin_accept(id):

    # ================= ADMIN SESSION CHECK =================
    if 'admin_id' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    # ================= APPROVE APPOINTMENT =================
    cur.execute("""
        UPDATE appointments
        SET status='Approved'
        WHERE appointment_id=%s
    """, (id,))

    mysql.connection.commit()

    # ================= GET PATIENT DETAILS =================
    cur.execute("""
        SELECT email, name, appointment_id
        FROM appointments
        WHERE appointment_id=%s
    """, (id,))

    data = cur.fetchone()
    cur.close()

    if data:

        patient_email = data[0]
        patient_name = data[1]
        appointment_id = data[2]

        # ================= VIEW LINK =================
        view_link = f"http://127.0.0.1:5000/appointment_form/{appointment_id}"

        # ================= LOGO LINK =================
        logo_url = "http://127.0.0.1:5000/static/logo.png"

        # ================= PROFESSIONAL EMAIL =================
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        </head>

        <body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">

        <div style="max-width:620px;margin:25px auto;background:#ffffff;
        border-radius:12px;overflow:hidden;border:1px solid #dddddd;
        box-shadow:0 4px 15px rgba(0,0,0,0.08);">

            <!-- HEADER -->
            <div style="background:#0d6efd;padding:22px;text-align:center;color:white;">

                <img src="{logo_url}" width="70"
                style="display:block;margin:0 auto 10px auto;">

                <h2 style="margin:0;">Heal Care Hospital</h2>

                <p style="margin:6px 0 0;font-size:13px;">
                    Appointment Approval Notification
                </p>

            </div>

            <!-- BODY -->
            <div style="padding:28px;">

                <p style="font-size:16px;color:#222;">
                    Dear <b>{patient_name}</b>,
                </p>

                <p style="font-size:15px;line-height:1.7;color:#444;">
                    We are pleased to inform you that your appointment request has been
                    <b style="color:#198754;">APPROVED</b> by our administration team.
                </p>

                <!-- INFO BOX -->
                <div style="background:#eaf7ee;padding:16px;border-radius:8px;
                border-left:5px solid #198754;margin:22px 0;">

                    <p style="margin:0;font-size:14px;line-height:1.8;color:#333;">
                        <b>Appointment ID:</b> {appointment_id}<br>
                        <b>Status:</b> Approved<br>
                        <b>Approved By:</b> Hospital Admin
                    </p>

                </div>

                <!-- BUTTON -->
                <div style="text-align:center;margin:30px 0;">

                    <a href="{view_link}"
                    style="background:#0d6efd;color:white;
                    padding:13px 28px;
                    text-decoration:none;
                    border-radius:6px;
                    font-weight:bold;
                    display:inline-block;">
                    View Appointment Form
                    </a>

                </div>

                <p style="font-size:13px;color:#666;line-height:1.7;">
                    Please arrive 15 minutes before your scheduled appointment time.
                    Kindly carry this confirmation email while visiting the hospital.
                </p>

            </div>

            <!-- FOOTER -->
            <div style="background:#f1f1f1;text-align:center;
            padding:14px;font-size:12px;color:#666;">

                © 2026 Heal Care Hospital | 24/7 Healthcare Services

            </div>

        </div>

        </body>
        </html>
        """

        # ================= SEND EMAIL =================
        msg = Message(
            subject="✅ Appointment Approved - Heal Care Hospital",
            sender=app.config['MAIL_USERNAME'],
            recipients=[patient_email]
        )

        msg.html = html_body
        mail.send(msg)

    return redirect('/view_appointments')

@app.route('/delete_appointment/<int:id>')
def delete_appointment(id):

    if 'admin' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute("""
    DELETE FROM appointments
    WHERE appointment_id=%s
    """,(id,))

    mysql.connection.commit()
    cur.close()

    return redirect(request.referrer)
@app.route('/admin_reject/<int:id>')
def admin_reject(id):

    # ================= ADMIN SESSION CHECK =================
    if 'admin_id' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    # ================= REJECT APPOINTMENT =================
    cur.execute("""
        UPDATE appointments
        SET status='Canceled',
            cancel_reason='Cancelled by admin',
            canceled_by='Admin'
        WHERE appointment_id=%s
    """, (id,))

    mysql.connection.commit()

    # ================= GET PATIENT DETAILS =================
    cur.execute("""
        SELECT email, name, appointment_id
        FROM appointments
        WHERE appointment_id=%s
    """, (id,))

    data = cur.fetchone()
    cur.close()

    if data:

        patient_email = data[0]
        patient_name = data[1]
        appointment_id = data[2]

        # Hospital logo
        logo_url = "http://127.0.0.1:5000/static/logo.png"

        # ================= PROFESSIONAL REJECTION EMAIL =================
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        </head>

        <body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">

        <div style="max-width:620px;margin:25px auto;background:#ffffff;
        border-radius:12px;overflow:hidden;border:1px solid #dddddd;
        box-shadow:0 4px 15px rgba(0,0,0,0.08);">

            <!-- HEADER -->
            <div style="background:#dc3545;padding:22px;text-align:center;color:white;">

                <img src="{logo_url}" width="70"
                style="display:block;margin:0 auto 10px auto;">

                <h2 style="margin:0;">Heal Care Hospital</h2>

                <p style="margin:6px 0 0;font-size:13px;">
                    Appointment Status Update
                </p>

            </div>

            <!-- BODY -->
            <div style="padding:28px;">

                <p style="font-size:16px;color:#222;">
                    Dear <b>{patient_name}</b>,
                </p>

                <p style="font-size:15px;line-height:1.7;color:#444;">
                    We regret to inform you that your appointment request has been
                    <b style="color:#dc3545;">CANCELLED</b> by the hospital administration.
                </p>

                <!-- INFO BOX -->
                <div style="background:#fff5f5;padding:16px;border-radius:8px;
                border-left:5px solid #dc3545;margin:22px 0;">

                    <p style="margin:0;font-size:14px;line-height:1.8;color:#333;">
                        <b>Appointment ID:</b> {appointment_id}<br>
                        <b>Status:</b> Cancelled<br>
                        <b>Reason:</b> Cancelled by Admin
                    </p>

                </div>

                <p style="font-size:14px;color:#555;line-height:1.7;">
                    We sincerely apologize for the inconvenience caused.
                    You may schedule a new appointment at your convenience
                    or contact our reception desk for further assistance.
                </p>

            </div>

            <!-- FOOTER -->
            <div style="background:#f1f1f1;text-align:center;
            padding:14px;font-size:12px;color:#666;">

                © 2026 Heal Care Hospital | 24/7 Healthcare Services

            </div>

        </div>

        </body>
        </html>
        """

        # ================= SEND EMAIL =================
        msg = Message(
            subject="❌ Appointment Cancelled - Heal Care Hospital",
            sender=app.config['MAIL_USERNAME'],
            recipients=[patient_email]
        )

        msg.html = html_body
        mail.send(msg)

    return redirect('/view_appointments')

@app.route('/reschedule/<int:appointment_id>', methods=['GET','POST'])
def reschedule(appointment_id):

    if 'patient_id' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    if request.method == 'POST':

        doctor_id = request.form['doctor']
        department = request.form['department']
        new_date = request.form['date']
        new_time = request.form['time']

        cur.execute("""
        UPDATE appointments
        SET doctor_id=%s,
            specialization=%s,
            appointment_date=%s,
            appointment_time=%s,
            status='Pending'
        WHERE appointment_id=%s
        """,(doctor_id,department,new_date,new_time,appointment_id))

        mysql.connection.commit()
        cur.close()

        flash("Appointment Rescheduled Successfully!", "success")

        return redirect('/my_appointments')

    # get appointment
    cur.execute("SELECT * FROM appointments WHERE appointment_id=%s",(appointment_id,))
    appointment = cur.fetchone()

    # get departments
    cur.execute("SELECT DISTINCT specialization FROM doctors WHERE status='Active'")
    departments = [d[0] for d in cur.fetchall()]

    cur.close()

    return render_template("reschedule_appointment.html",
                           appointment=appointment,
                           departments=departments)

from datetime import datetime, timedelta

@app.route("/generate_slots/<doctor_id>/<date>")
def generate_slots(doctor_id, date):

    cur = mysql.connection.cursor()

    # get doctor shift
    cur.execute("SELECT shift_start_hm, shift_end_hm FROM doctors WHERE doctor_id=%s",(doctor_id,))
    shift = cur.fetchone()

    start = datetime.strptime(shift[0], "%H:%M")
    end = datetime.strptime(shift[1], "%H:%M")

    while start < end:

        next_time = start + timedelta(minutes=30)

        slot = start.strftime("%H:%M") + " - " + next_time.strftime("%H:%M")

        cur.execute("""
        INSERT INTO doctor_slots(doctor_id,slot_date,slot_time)
        VALUES(%s,%s,%s)
        """,(doctor_id,date,slot))

        start = next_time

    mysql.connection.commit()

    return "Slots Generated"

from flask import jsonify

from datetime import datetime, timedelta

@app.route('/get_slots/<doctor_id>/<date>')
def get_slots(doctor_id, date):

    cur = mysql.connection.cursor()

    # Get doctor shift
    cur.execute("""
    SELECT shift_start_hm, shift_end_hm, shift_type
    FROM doctors WHERE doctor_id=%s
    """,(doctor_id,))
    
    doctor = cur.fetchone()

    shift_start = doctor[0]
    shift_end = doctor[1]
    shift_type = doctor[2]

    from datetime import datetime, timedelta

    start = datetime.strptime(str(shift_start), "%H:%M")
    end = datetime.strptime(str(shift_end), "%H:%M")

    slots = []

    while start < end:

        slot_start = start.strftime("%H:%M")
        slot_end = (start + timedelta(minutes=30)).strftime("%H:%M")

        slot = f"{slot_start} - {slot_end}"

        # Check booking
        cur.execute("""
          SELECT * FROM appointments
            WHERE doctor_id=%s 
            AND appointment_date=%s 
            AND appointment_time=%s
            AND status IN ('Pending','Approved')
            """,(doctor_id,date,slot))
        
        booked = cur.fetchone()

        slots.append({
            "time": slot,
            "status": "Booked" if booked else "Available"
        })

        start += timedelta(minutes=30)

    cur.close()

    return jsonify({
        "slots": slots,
        "shift": shift_type
    })

from datetime import datetime, timedelta
from flask import jsonify

@app.route('/slot_calendar/<doctor_id>/<date>')
def slot_calendar(doctor_id, date):

    cur = mysql.connection.cursor()

    # doctor shift
    cur.execute("SELECT shift_start_hm, shift_end_hm FROM doctors WHERE doctor_id=%s",(doctor_id,))
    shift = cur.fetchone()

    start = datetime.strptime(str(shift[0]), "%H:%M")
    end = datetime.strptime(str(shift[1]), "%H:%M")

    slots = []

    while start < end:

        slot_start = start.strftime("%H:%M")
        slot_end = (start + timedelta(minutes=30)).strftime("%H:%M")

        slot = f"{slot_start} - {slot_end}"

        # check booked
        cur.execute("""
        SELECT * FROM appointments
        WHERE doctor_id=%s AND appointment_date=%s AND appointment_time=%s
        """,(doctor_id,date,slot))

        booked = cur.fetchone()

        status = "Booked" if booked else "Available"

        slots.append({
            "slot": slot,
            "status": status
        })

        start += timedelta(minutes=30)

    cur.close()

    return jsonify(slots)


@app.route('/admin_day_appointments/<date>')
def admin_day_appointments(date):

    if 'admin' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute("""
    SELECT appointment_id,
           token,
           doctor_name,
           specialization,
           appointment_date,
           appointment_time,
           problem,
           status
    FROM appointments
    WHERE appointment_date=%s
    ORDER BY appointment_time
    """, (date,))

    appointments = cur.fetchall()

    cur.close()

    return render_template(
        "admin_day_appointments.html",
        appointments=appointments,
        date=date
    )


@app.route('/finish_appointment/<int:id>')
def finish_appointment(id):

    # ✅ Allow Doctor Login
    if 'doctor_id' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE appointments
        SET status='Finished'
        WHERE appointment_id=%s
    """, (id,))

    mysql.connection.commit()
    cur.close()

    return redirect('/doctor_appointments')
from datetime import datetime
import calendar


@app.route('/admin_calendar')
def admin_calendar():

    if 'admin' not in session:
        return redirect('/')

    # ✅ GET MONTH & YEAR FROM URL
    month = request.args.get('month')
    year = request.args.get('year')

    if not month or not year:
        today = datetime.now()
        month = today.month
        year = today.year
    else:
        month = int(month)
        year = int(year)

    cal = calendar.monthcalendar(year, month)

    cur = mysql.connection.cursor()

    # ✅ TOTAL APPOINTMENTS
    cur.execute("""
    SELECT DAY(appointment_date), COUNT(*)
    FROM appointments
    WHERE MONTH(appointment_date)=%s AND YEAR(appointment_date)=%s
    GROUP BY DAY(appointment_date)
    """,(month,year))
    counts = dict(cur.fetchall())

    # ✅ PENDING
    cur.execute("""
    SELECT DAY(appointment_date), COUNT(*)
    FROM appointments
    WHERE status='Pending' AND MONTH(appointment_date)=%s AND YEAR(appointment_date)=%s
    GROUP BY DAY(appointment_date)
    """,(month,year))
    pending_counts = dict(cur.fetchall())

    # ✅ APPROVED
    cur.execute("""
    SELECT DAY(appointment_date), COUNT(*)
    FROM appointments
    WHERE status='Approved' AND MONTH(appointment_date)=%s AND YEAR(appointment_date)=%s
    GROUP BY DAY(appointment_date)
    """,(month,year))
    approved_counts = dict(cur.fetchall())

    # ✅ REJECTED/CANCELED
    cur.execute("""
    SELECT DAY(appointment_date), COUNT(*)
    FROM appointments
    WHERE status IN ('Rejected','Canceled') 
    AND MONTH(appointment_date)=%s AND YEAR(appointment_date)=%s
    GROUP BY DAY(appointment_date)
    """,(month,year))
    rejected_counts = dict(cur.fetchall())

    # ✅ FINISHED
    cur.execute("""
    SELECT DAY(appointment_date), COUNT(*)
    FROM appointments
    WHERE status='Finished' 
    AND MONTH(appointment_date)=%s AND YEAR(appointment_date)=%s
    GROUP BY DAY(appointment_date)
    """,(month,year))
    finished_counts = dict(cur.fetchall())

    cur.close()

    return render_template(
        "admin_calendar.html",
        calendar=cal,
        counts=counts,
        pending_counts=pending_counts,
        approved_counts=approved_counts,
        rejected_counts=rejected_counts,
        finished_counts=finished_counts,
        month=month,
        year=year
    )

@app.route('/admin_free_slot/<int:id>')
def admin_free_slot(id):

    if 'admin' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    # 1️⃣ Get appointment details
    cur.execute("""
        SELECT doctor_id, appointment_date, appointment_time
        FROM appointments
        WHERE appointment_id=%s
    """, (id,))
    
    data = cur.fetchone()

    doctor_id = data[0]
    date = data[1]
    time = data[2]

    # 2️⃣ Mark appointment as Finished
    cur.execute("""
        UPDATE appointments
        SET status='Finished'
        WHERE appointment_id=%s
    """, (id,))

    # 3️⃣ OPTIONAL (IMPORTANT): Free slot logic
    # Since your system checks slots from appointments table,
    # marking as Finished automatically frees slot (because your slot API checks only booked ones)

    mysql.connection.commit()
    cur.close()

    return redirect(request.referrer)


@app.route('/profile')
def profile():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM patients WHERE patient_id=%s", (session['patient_id'],))
    patient = cur.fetchone()

    return render_template("profile.html", patient=patient)

import os
from werkzeug.utils import secure_filename
@app.route('/update_profile', methods=['POST'])
def update_profile():

    if 'patient_id' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    name = request.form.get('name')
    age = request.form.get('age')
    phone = request.form.get('phone')
    place = request.form.get('place')
    gender = request.form.get('gender')
    email = request.form.get('email')

    old_password = request.form.get("old_password")
    new_password = request.form.get("new_password")

    patient_id = session['patient_id']

    file = request.files.get('profile_pic')

    # Current password
    cur.execute("SELECT password FROM patients WHERE patient_id=%s", (patient_id,))
    current_password = cur.fetchone()[0]

    # Password logic
    if new_password and new_password.strip() != "":
        if old_password != current_password:
            flash("Old password incorrect", "danger")
            return redirect('/profile')

        password = new_password
    else:
        password = current_password

    # Upload image
    if file and file.filename != "":

        import os
        from werkzeug.utils import secure_filename

        ext = os.path.splitext(file.filename)[1]
        filename = str(patient_id) + ext

        filepath = os.path.join('static/uploads', filename)
        file.save(filepath)

        cur.execute("""
        UPDATE patients
        SET name=%s, age=%s, phone=%s, place=%s, gender=%s,
            email=%s, password=%s, profile_pic=%s
        WHERE patient_id=%s
        """, (name, age, phone, place, gender, email, password, filename, patient_id))

    else:

        cur.execute("""
        UPDATE patients
        SET name=%s, age=%s, phone=%s, place=%s, gender=%s,
            email=%s, password=%s
        WHERE patient_id=%s
        """, (name, age, phone, place, gender, email, password, patient_id))

    mysql.connection.commit()
    cur.close()

    flash("Profile Updated Successfully", "success")

    return redirect('/profile')

@app.route('/admin_day_appointments_json/<date>')
def admin_day_appointments_json(date):

    cur = mysql.connection.cursor()

    cur.execute("""
    SELECT name, doctor_name, appointment_time, status
    FROM appointments
    WHERE appointment_date=%s
    ORDER BY appointment_time
    """,(date,))

    data = []

    for row in cur.fetchall():
        data.append({
            "name": row[0],
            "doctor": row[1],
            "time": row[2],
            "status": row[3]
        })

    cur.close()

    return jsonify(data)


@app.route('/view_patient/<id>')
def view_patient(id):
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM patients WHERE patient_id=%s", (id,))
    patient = cursor.fetchone()

    # total appointments
    cursor.execute("""
        SELECT COUNT(*) FROM appointments WHERE patient_id=%s
    """, (id,))
    total_appointments = cursor.fetchone()[0]

    # appointment history
    cursor.execute("""
        SELECT appointment_date, appointment_time, doctor_name, status, problem
        FROM appointments
        WHERE patient_id=%s
        ORDER BY appointment_date DESC
    """, (id,))
    appointments = cursor.fetchall()

    return render_template(
        "view_patient.html",
        patient=patient,
        total_appointments=total_appointments,
        appointments=appointments
    )

@app.route('/add_note/<patient_id>', methods=['POST'])
def add_note(patient_id):
    note = request.form['note']

    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO patient_notes (patient_id, note) VALUES (%s, %s)",
        (patient_id, note)
    )
    mysql.connection.commit()

    flash("✅ Note added successfully!", "success")

    return redirect(f"/view_patient/{patient_id}")   # ✅ IMPORTANT FIX


@app.route('/delete_note/<patient_id>/<note>')
def delete_note(patient_id, note):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        DELETE FROM patient_notes 
        WHERE patient_id=%s AND note=%s
    """, (patient_id, note))

    mysql.connection.commit()
    cursor.close()

    flash("Note deleted!", "danger")
    return redirect(f"/view_patient/{patient_id}")


@app.route('/add_patient', methods=['POST'])
def add_patient():
    cursor = mysql.connection.cursor()

    name = request.form['name']
    age = request.form['age']
    phone = request.form['phone']
    place = request.form['place']

    # 🔥 get doctor_id from session
    doctor_id = session.get('doctor_id')

    cursor.execute("""
    INSERT INTO patients (name, age, phone, place, doctor_id)
    VALUES (%s, %s, %s, %s, %s)
    """, (name, age, phone, place, doctor_id))

    mysql.connection.commit()

    return redirect('/doctor_patients')


from datetime import date

@app.route('/pat_reports')
def pat_reports():

    if 'patient_id' not in session:
        return redirect('/')

    patient_id = session['patient_id']

    cur = mysql.connection.cursor()

    # patient details
    cur.execute("SELECT * FROM patients WHERE patient_id=%s", (patient_id,))
    patient = cur.fetchone()

    # appointments history
    cur.execute("""
        SELECT appointment_date,
               appointment_time,
               doctor_name,
               status,
               problem
        FROM appointments
        WHERE patient_id=%s
        ORDER BY appointment_date DESC
    """, (patient_id,))

    appointments = cur.fetchall()

    cur.close()

    return render_template(
        'patient_report.html',
        patient=patient,
        appointments=appointments,
        current_date=date.today().strftime("%d-%m-%Y")
    )

@app.route('/doctor_accept/<int:id>')
def doctor_accept(id):

    if 'doctor_id' not in session:
        return redirect('/')

    doctor_id = session['doctor_id']
    cur = mysql.connection.cursor()

    # ✅ Approve appointment
    cur.execute("""
        UPDATE appointments
        SET status='Approved'
        WHERE appointment_id=%s AND doctor_id=%s
    """, (id, doctor_id))

    mysql.connection.commit()

    # ✅ Get patient details
    cur.execute("""
        SELECT email, name, appointment_id
        FROM appointments
        WHERE appointment_id=%s
    """, (id,))

    data = cur.fetchone()
    cur.close()

    if data:
        patient_email = data[0]
        patient_name = data[1]
        appointment_id = data[2]

        # ✅ Correct view link
        view_link = f"http://127.0.0.1:5000/appointment_form/{appointment_id}"

        # ================= PROFESSIONAL EMAIL =================
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        </head>

        <body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">

        <div style="max-width:600px;margin:20px auto;background:#ffffff;
        border-radius:10px;overflow:hidden;border:1px solid #e6e6e6;">

        <!-- HEADER -->
        <div style="background:#0d6efd;color:white;padding:25px;text-align:center;">
            <h2 style="margin:0;">🏥 Heal Care Hospital</h2>
            <p style="margin:5px 0 0;font-size:13px;">Appointment Approval Notification</p>
        </div>

        <!-- BODY -->
        <div style="padding:25px;">

            <p style="font-size:16px;">Dear <b>{patient_name}</b>,</p>

            <p style="font-size:15px;line-height:1.6;color:#333;">
                We are pleased to inform you that your appointment request has been
                <b style="color:green;">APPROVED</b> by our doctor.
            </p>

            <!-- INFO BOX -->
            <div style="background:#e8f5e9;padding:15px;border-radius:8px;
            margin:20px 0;border-left:5px solid #28a745;">
                <p style="margin:0;font-size:14px;">
                    <b>Appointment ID:</b> {appointment_id}<br>
                    <b>Status:</b> Approved<br>
                    <b>Hospital:</b> Heal Care Hospital
                </p>
            </div>

            <!-- BUTTON -->
            <div style="text-align:center;margin:30px 0;">
                <a href="{view_link}"
                   style="background:#0d6efd;color:white;
                   padding:12px 28px;text-decoration:none;
                   border-radius:6px;font-weight:bold;
                   display:inline-block;">
                   View Appointment Details
                </a>
            </div>

            <p style="font-size:13px;color:#666;line-height:1.6;">
                Please arrive 15 minutes before your scheduled time.<br>
                Bring this confirmation email or QR code for verification at the hospital.
            </p>

        </div>

        <!-- FOOTER -->
        <div style="background:#f1f1f1;text-align:center;
        padding:12px;font-size:12px;color:#666;">
            © 2026 Heal Care Hospital | All Rights Reserved
        </div>

        </div>

        </body>
        </html>
        """

        # ================= SEND EMAIL =================
        msg = Message(
            subject="✅ Appointment Approved - Heal Care Hospital",
            sender=app.config['MAIL_USERNAME'],
            recipients=[patient_email]
        )

        msg.html = html_body
        mail.send(msg)

    return redirect('/doctor_appointments')


@app.route('/make_pending/<int:id>')
def make_pending(id):

    cur = mysql.connection.cursor()

    cur.execute("UPDATE appointments SET status='Pending' WHERE appointment_id=%s", (id,))
    mysql.connection.commit()

    cur.close()

    return """
    <script>
    alert('Status Changed to Pending');
    window.history.back();
    </script>
    """

@app.route('/send_otp', methods=['POST'])
def send_otp():

    patient_id = request.form['patient_id']
    method = request.form['method']
    value = request.form['value']

    cur = mysql.connection.cursor()

    if method == "mail":
        cur.execute("""
        SELECT * FROM patients
        WHERE patient_id=%s AND email=%s
        """,(patient_id,value))

    else:
        cur.execute("""
        SELECT * FROM patients
        WHERE patient_id=%s AND phone=%s
        """,(patient_id,value))

    user = cur.fetchone()

    if user:

        import random
        otp = str(random.randint(100000,999999))

        session['reset_otp'] = otp
        session['reset_patient'] = patient_id

        print("OTP =", otp)   # test first

        return "OTP Sent"

    else:
        return "Invalid Details"






if __name__ == "__main__":
    app.run(debug=True)