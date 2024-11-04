import numpy as np
from ultralytics import YOLO
import cv2
import math
import time
import os
from flask import Flask, render_template, send_from_directory, request, redirect, url_for, session, flash
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import threading
from collections import defaultdict
import requests
from flask_sqlalchemy import SQLAlchemy

# Khởi tạo Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'sometotallyrandomandlongsecretkey123'

# Cấu hình cơ sở dữ liệu
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'  # Thay đổi đường dẫn cơ sở dữ liệu nếu cần
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Định nghĩa mô hình User
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(150))
    password = db.Column(db.String(150), nullable=False)

# Đường dẫn đến thư mục lưu media
MEDIA_FOLDER = os.path.join(app.static_folder, 'media')
if not os.path.exists(MEDIA_FOLDER):
    os.makedirs(MEDIA_FOLDER)

# Tài khoản đăng nhập với mật khẩu đã được hash
USERNAME = '0944700040'
PASSWORD_HASH = generate_password_hash('1234abcd')

# -------- ROUTES FOR FLASK WEB APP --------
SECRET_KEY = '6Le9El8qAAAAAGoEv7maM17g4TxO09lnAFFAmTNV'

@app.route('/')
def home():
    return redirect(url_for('login'))  # Chuyển hướng luôn đến trang đăng nhập

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        recaptcha_response = request.form.get('g-recaptcha-response')

        if not recaptcha_response:
            flash('Vui lòng hoàn thành reCAPTCHA')
            return render_template('login.html')

        # Xác thực reCAPTCHA
        recaptcha_url = 'https://www.google.com/recaptcha/api/siteverify'
        recaptcha_payload = {
            'secret': SECRET_KEY,
            'response': recaptcha_response
        }
        recaptcha_request = requests.post(recaptcha_url, data=recaptcha_payload)
        recaptcha_result = recaptcha_request.json()

        if recaptcha_result.get('success'):
            # Kiểm tra username và mật khẩu
            if username == USERNAME and check_password_hash(PASSWORD_HASH, password):
                session['logged_in'] = True
                return redirect(url_for('index'))
            else:
                flash('Đăng nhập thất bại')
        else:
            flash('reCAPTCHA không hợp lệ. Vui lòng thử lại.')
    return render_template('login.html')

@app.route('/index')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    video_extensions = ['.mp4', '.webm', '.ogg']

    media_files = {}

    for filename in os.listdir(MEDIA_FOLDER):
        filepath = os.path.join(MEDIA_FOLDER, filename)
        if os.path.isfile(filepath):
            extension = os.path.splitext(filename)[1].lower()
            uploaded_time = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%d/%m/%Y %H:%M:%S')
            date = uploaded_time.split(' ')[0]

            if date not in media_files:
                media_files[date] = {'images': [], 'videos': []}

            if extension in image_extensions:
                media_files[date]['images'].append((filename, uploaded_time))
            elif extension in video_extensions:
                media_files[date]['videos'].append((filename, uploaded_time))

    # Sort by date in descending order
    sorted_media_files = dict(sorted(media_files.items(), key=lambda item: datetime.strptime(item[0], '%d/%m/%Y'), reverse=True))

    return render_template('index.html', media_files=sorted_media_files)

@app.route('/account_info')
def account_info():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    video_extensions = ['.mp4', '.webm', '.ogg']

    total_images = 0
    total_videos = 0
    recent_falls = []

    # Biến lưu trữ số lượng ảnh và video theo ngày
    fall_dates = defaultdict(lambda: {'images': 0, 'videos': 0})

    for filename in os.listdir(MEDIA_FOLDER):
        filepath = os.path.join(MEDIA_FOLDER, filename)
        extension = os.path.splitext(filename)[1].lower()
        uploaded_time = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%d/%m/%Y %H:%M:%S')
        date = datetime.strptime(uploaded_time, '%d/%m/%Y %H:%M:%S').date()  # Chỉ lấy ngày

        if extension in image_extensions:
            total_images += 1
            recent_falls.append({'time': uploaded_time, 'type': 'Ảnh', 'filename': filename})
            fall_dates[date]['images'] += 1  # Cập nhật số lượng ảnh cho ngày tương ứng
        elif extension in video_extensions:
            total_videos += 1
            recent_falls.append({'time': uploaded_time, 'type': 'Video', 'filename': filename})
            fall_dates[date]['videos'] += 1  # Cập nhật số lượng video cho ngày tương ứng

    # Sắp xếp danh sách các trường hợp té ngã gần đây theo thời gian giảm dần
    recent_falls = sorted(recent_falls, key=lambda x: x['time'], reverse=True)[:10]  # Lấy 10 trường hợp gần nhất

    last_login = session.get('last_login', 'Không xác định')

    # Dữ liệu cho biểu đồ
    chart_labels = [date.strftime('%Y-%m-%d') for date in fall_dates.keys()]
    chart_images = [int(fall_dates[date]['images']) for date in fall_dates.keys()]  # Đảm bảo số nguyên cho ảnh
    chart_videos = [int(fall_dates[date]['videos']) for date in fall_dates.keys()]  # Đảm bảo số nguyên cho video

    return render_template('account_info.html', username=USERNAME, total_images=total_images, total_videos=total_videos,
                           recent_falls=recent_falls, last_login=last_login, chart_labels=chart_labels,
                           chart_images=chart_images, chart_videos=chart_videos)

@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(MEDIA_FOLDER, filename)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/edit_account', methods=['POST'])
def edit_account():
    if not session.get('logged_in'):  # Kiểm tra nếu người dùng đã đăng nhập
        return redirect(url_for('login'))

    phone = request.form['phone']
    new_password = request.form['password']
    confirm_password = request.form['confirm_password']

    if new_password == confirm_password:
        # Cập nhật số điện thoại và mật khẩu ở đây
        update_user_info(phone, new_password)
        flash("Đổi thông tin thành công!", "success")
    else:
        flash("Mật khẩu chưa trùng khớp!", "danger")

    return redirect(url_for('account_info'))

def update_user_info(phone, new_password):
    user = User.query.filter_by(username=USERNAME).first()  # Tìm người dùng theo tên đăng nhập
    if user:
        user.phone = phone  # Cập nhật số điện thoại
        user.password = generate_password_hash(new_password)  # Cập nhật mật khẩu đã được hash
        db.session.commit()  # Lưu thay đổi vào cơ sở dữ liệu

if __name__ == '__main__':
    threading.Thread(target=yolo_detection, daemon=True).start()  # Chạy hàm yolo_detection
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))  # Chạy ứng dụng Flask
