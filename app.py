from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # ใช้ SQLite
app.config['SQLALCHEMY_BINDS'] = {
    'patients': 'sqlite:///info.db'  # ฐานข้อมูลสำหรับข้อมูลผู้ป่วย
}
db = SQLAlchemy(app)

class User(db.Model):
    __bind_key__ = 'patients'  # กำหนดให้ใช้ฐานข้อมูล users.db
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
# ตารางข้อมูลผู้ป่วย
class Patient(db.Model):
    __bind_key__ = 'patients'  # กำหนดให้ใช้ฐานข้อมูล info.db
    id = db.Column(db.Integer, primary_key=True)
    dental_num = db.Column(db.String(100))
    name = db.Column(db.String(100))
    surname = db.Column(db.String(100))
    diagnosis = db.Column(db.String(500))  # สามารถเก็บหลายๆ ค่าได้
    icd10 = db.Column(db.String(500))  # เก็บหลายๆ ค่า
    visit_type = db.Column(db.String(100))
    date = db.Column(db.String(100))  # วันที่ล่าสุด


    def __init__(self, name, surname, dental_num, visit_type, date, diagnosis=None, icd10=None):
        self.name = name
        self.surname = surname
        self.dental_num = dental_num
        self.visit_type = visit_type
        self.date = date
        self.diagnosis = diagnosis
        self.icd10 = icd10

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_or_username = request.form['email_or_username']
        password = request.form['password']
        user = User.query.filter((User.email == email_or_username) | (User.username == email_or_username)).first()
        if user and user.check_password(password):
            session['username'] = user.username  # เก็บ username ใน session
            return redirect(url_for('main'))  # เปลี่ยนไปยังหน้า main หลังจากเข้าสู่ระบบสำเร็จ
        else:
            return jsonify(success=False, message="Invalid User")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)  # ลบข้อมูล session ของ username
    return redirect(url_for('index'))

@app.context_processor
def inject_user():
    return dict(current_user=session.get('username'))

@app.route('/reg', methods=['GET', 'POST'])
def reg():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('username')

        existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            return {"success": False, "message": "Have account already!"}, 400

        new_user = User(email=email, username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
    
        return redirect(url_for('login'))
    return render_template('reg.html')


@app.route('/main')
def main():
    if 'user_id' in session:
        return render_template('main.html')
    return redirect(url_for('login'))

@app.route('/search', methods=['GET', 'POST'])
def search():
    # ดึงข้อมูลทั้งหมดจากฐานข้อมูลผู้ป่วย
    patients = Patient.query.all()

    # ส่งข้อมูลผู้ป่วยไปยังเทมเพลต
    return render_template('search.html', patients=patients)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        dental_num = request.form['dental_num']
        visit_type = request.form['visit_type']
        date = request.form['date']

        # รับข้อมูลการวินิจฉัยและรหัส ICD-10
        diagnoses = request.form.getlist('diagnosis[]')
        icd10 = request.form.getlist('icd10[]')

        # เก็บการวินิจฉัยและรหัส ICD-10 เป็นข้อความ
        diagnosis_str = ', '.join(diagnoses)
        icd10_str = ', '.join(icd10)

        # สร้างผู้ป่วยใหม่
        new_patient = Patient(
            name=name,
            surname=surname,
            dental_num=dental_num,
            visit_type=visit_type,
            date=date,
            diagnosis=diagnosis_str,
            icd10=icd10_str
        )
        
        # บันทึกข้อมูลในฐานข้อมูล
        db.session.add(new_patient)
        db.session.commit()

        return redirect(url_for('add'))  # ไปที่หน้า add หลังจากเพิ่มข้อมูล
    return render_template('add.html')

@app.route('/add_icd_diagnosis', methods=['POST'])
def add_icd_diagnosis():
    patient_id = request.form.get('patient_id')
    diagnosis = request.form.get('diagnosis')
    icd10 = request.form.get('icd10')
    date = request.form.get('date')

    # ค้นหาผู้ป่วยจาก patient_id
    patient = Patient.query.get(patient_id)
    if patient:
        # เพิ่มข้อมูลใหม่ในฟิลด์ ICD และ Diagnosis
        if patient.diagnosis:
            patient.diagnosis += "," + diagnosis
        else:
            patient.diagnosis = diagnosis

        if patient.icd10:
            patient.icd10 += "," + icd10
        else:
            patient.icd10 = icd10

        # เพิ่มวันที่
        patient.date = date

        db.session.commit()

        # ส่งกลับผลลัพธ์ (สามารถเลือก redirect หรือแจ้งผลการเพิ่ม)
        flash('Data added successfully!')
        return redirect(url_for('search'))  # เปลี่ยนไปยังหน้าค้นหาหลังจากเพิ่มข้อมูล
    return jsonify(success=False, message="Patient not found"), 404


with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)

