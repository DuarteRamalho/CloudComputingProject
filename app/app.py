from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import io
from datetime import datetime
from file_storage import FileStorage

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = '/app/uploads'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

file_storage = FileStorage()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    version = db.Column(db.Integer, default=1)
    size = db.Column(db.Integer, nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.String(255))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    files = File.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', files=files)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            log_action(user.id, 'login')
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('register.html')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists')
            return render_template('register.html')

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    log_action(current_user.id, 'logout')
    logout_user()
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))

    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))

    filename = file.filename

    if file and filename:
        try:
            
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  

            existing_file = File.query.filter_by(filename=filename, user_id=current_user.id).first()

            if existing_file:
                existing_file.version += 1
                existing_file.size = file_size
                existing_file.upload_date = datetime.utcnow()
            else:
                new_file = File(filename=filename, size=file_size, user_id=current_user.id)
                db.session.add(new_file)


            save_success = file_storage.save_file(file, filename, current_user.id)
            if save_success:
                db.session.commit()
                log_action(current_user.id, 'upload', f'File: {filename}')
                flash('File uploaded successfully')
            else:
                db.session.rollback()  
                flash('Error saving file to S3')

        except Exception as e:
            print(f"Upload error: {str(e)}")
            db.session.rollback()
            flash('Error processing file upload')

    return redirect(url_for('index'))


@app.route('/download/<int:file_id>')
@login_required
def download_file(file_id):

    file = File.query.get_or_404(file_id)


    if file.user_id != current_user.id:
        flash('Unauthorized access')
        return redirect(url_for('index'))


    file_content = file_storage.download_file(file.filename, current_user.id)
    

    if file_content is None:
        flash('Error downloading file')
        return redirect(url_for('index'))


    log_action(current_user.id, 'download', f'File: {file.filename}')


    if not isinstance(file_content, (bytes, bytearray)):
        flash('Downloaded file content is not in the expected format')
        return redirect(url_for('index'))


    return send_file(io.BytesIO(file_content),
                     mimetype='application/octet-stream',
                     as_attachment=True,
                     download_name=file.filename)


@app.route('/logs')
@login_required
def logs():
    log_entries = LogEntry.query.filter_by(user_id=current_user.id).order_by(LogEntry.timestamp.desc()).all()
    return render_template('logs.html', log_entries=log_entries)

def log_action(user_id, action, details=None):
    log_entry = LogEntry(user_id=user_id, action=action, details=details)
    db.session.add(log_entry)
    db.session.commit()

if __name__ == '__main__':
    if not file_storage.test_connection():
        print("Warning: S3 connection test failed!")
    
    db.create_all()
    app.run(host='0.0.0.0', port=5000)

