from flask import Flask, request, jsonify, send_from_directory
import uuid
import os
from PIL import Image
from werkzeug.utils import secure_filename
from ultralytics import YOLO
from flask_cors import CORS
from urllib.parse import quote_plus
import cv2
import numpy as np
import threading
from functools import wraps
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from werkzeug.security import check_password_hash, generate_password_hash
from promptpay import qrcode
import base64
from io import BytesIO
import hashlib
import json
import requests
import pytesseract
import re
from PIL import Image, ImageEnhance, ImageFilter
from flask import Flask, redirect, url_for
from flask_dance.contrib.google import make_google_blueprint, google
from dotenv import load_dotenv
from flask import render_template  
import smtplib
import secrets
from email.message import EmailMessage
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail, Message
import random
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote  
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from gradio_client import Client, handle_file
from zoneinfo import ZoneInfo
import shutil
import jwt

# การตั้งค่า Flask
app = Flask(__name__)
CORS(app)
 
load_dotenv()
 
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv("EMAIL_USER"),
    MAIL_PASSWORD=os.getenv("EMAIL_PASS"),
    MAIL_DEFAULT_SENDER='Phurinsukman3@gmail.com'  # ตั้งค่าอีเมลผู้ส่ง
)
 
mail = Mail(app)
 
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = "https://project-api-objectxify.onrender.com/auth/google/callback"

# เชื่อมต่อ MongoDB
uri = "mongodb+srv://66020981:Phurin192547@project-api.tsr0e8c.mongodb.net/?retryWrites=true&w=majority&appName=Project-API"
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
 
db = client["api_database"]
users_collection = db["users"]
api_keys_collection = db["api_keys"]
orders_collection = db["orders"]
otp_collection = db["otp_reset"]
 
 
# หน้าแรก
@app.route('/')
def home():
    # ใช้ relative path ไปยังโฟลเดอร์ 'home page'
    return send_from_directory(os.path.join(os.getcwd(), 'homepage'), 'index.html')
 
# เพิ่ม route สำหรับไฟล์อื่นๆ ที่อยู่ในโปรเจกต์
@app.route('/<path:filename>')
def serve_other_files(filename):
    # ให้ Flask สามารถเข้าถึงไฟล์จากทุกโฟลเดอร์ในโปรเจกต์
    return send_from_directory(os.getcwd(), filename)
 
# เพิ่ม route สำหรับไฟล์ CSS, JS ที่อยู่ในโฟลเดอร์ 'home page'
@app.route('/homepage/<path:filename>')
def serve_home_page_files(filename):
    # ให้ Flask สามารถเข้าถึงไฟล์ CSS และ JS ในโฟลเดอร์ 'home page'
    return send_from_directory(os.path.join(os.getcwd(), 'homepage'), filename)
 
# ฟังก์ชันสำหรับสมัครสมาชิก
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json  # รับข้อมูล JSON
    email = data.get("email")
    username = data.get("username")
    password = data.get("password")
 
    # ตรวจสอบว่าอีเมล, ชื่อผู้ใช้, และรหัสผ่านไม่ว่าง
    if not email or not username or not password:
        return jsonify({"message": "All fields are required"}), 400
 
    # ตรวจสอบว่าอีเมลนี้เคยลงทะเบียนแล้วหรือไม่
    if users_collection.find_one({"email": email}):
        return jsonify({"message": "Email already exists"}), 400
 
    # แฮชรหัสผ่าน
    hashed_password = generate_password_hash(password, method="pbkdf2:sha256", salt_length=8)
   
    # เพิ่มข้อมูลผู้ใช้ใหม่
    users_collection.insert_one({"email": email, "username": username, "password": hashed_password})
 
    return jsonify({"message": "Signup successful"}), 201
 
# ฟังก์ชันสำหรับล็อกอิน
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()  # รับข้อมูลจาก request body
    email = data.get('email')
    password = data.get('password')
 
    # ตรวจสอบว่าอีเมลและรหัสผ่านไม่ได้ว่าง
    if not email:
        return jsonify({'error': 'Email is required'}), 400
 
    # ค้นหาผู้ใช้ในฐานข้อมูลตาม email
    user = users_collection.find_one({"email": email})
 
    # หากผู้ใช้ไม่พบ
    if not user:
        return jsonify({'error': 'User not found'}), 404
 
    # ตรวจสอบผู้ใช้ที่ล็อกอินด้วย Google (ผู้ที่ไม่มีรหัสผ่าน)
    if user.get('password') is None:
        # ผู้ใช้ล็อกอินด้วย Google ให้ข้ามการตรวจสอบรหัสผ่าน
        return jsonify({'message': 'Login successful with Google'}), 200
 
    # ตรวจสอบรหัสผ่าน
    if not password:
        return jsonify({'error': 'Password is required'}), 400
 
    # ตรวจสอบรหัสผ่าน
    if not check_password_hash(user['password'], password):
        return jsonify({'error': 'Incorrect password'}), 400
 
    return jsonify({'message': 'Login successful'}), 200
 
# โฟลเดอร์สำหรับอัปโหลด
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
 
# ฟังก์ชันตรวจสอบประเภทไฟล์ (รองรับทุกประเภท)
def allowed_file(filename):
    return '.' in filename  # ตรวจสอบว่ามี "." ในชื่อไฟล์
 
# ฟังก์ชันตรวจสอบว่าเป็นไฟล์ภาพจริง
def is_image(file_path):
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except (IOError, SyntaxError):
        return False
 
# ฟังก์ชันแปลง .jfif เป็น .jpg
def convert_jfif_to_jpg(input_path):
    output_path = input_path.rsplit('.', 1)[0] + '.jpg'
    with Image.open(input_path) as img:
        img.convert('RGB').save(output_path, 'JPEG')
    os.remove(input_path)  # ลบไฟล์เดิม
    return output_path
 
# ฟังก์ชันสำหรับลบไฟล์
def delete_file(file_path):
    try:
        os.remove(file_path)
        print(f"Deleted file: {file_path}")
    except Exception as e:
        print(f"Error deleting file: {e}")

# API วิเคราะห์ภาพ
@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    try:
        api_key = request.headers.get('x-api-key')
        api_key_data = api_keys_collection.find_one({"api_key": api_key})
        if not api_key_data:
            return jsonify({'error': 'Invalid API Key'}), 401

        quota = int(api_key_data['quota'])
        if quota != -1 and quota <= 0:
            return jsonify({'error': 'Quota exceeded'}), 400

        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']
        ext = file.filename.rsplit('.', 1)[-1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        if not is_image(file_path):
            os.remove(file_path)
            return jsonify({'error': 'Invalid image'}), 400

        # ส่ง model_types ทั้งหมดในครั้งเดียว
        client = Client("Phurin1/best-por")

        detections = []
        image_url = None

        # ✅ เริ่มลูป model_type อย่างถูกต้อง
        result = client.predict(
            image=handle_file(file_path),
            model_types=api_key_data['analysis_types'],
            thresholds=api_key_data['thresholds'],
            api_name="/predict"
        )

        output_image = result[0]
        detection_data = json.loads(result[1])

        # บันทึกไฟล์ผลลัพธ์แค่ครั้งเดียว
        processed_filename = f"processed_{uuid.uuid4()}.jpg"
        processed_path = os.path.join(app.config['UPLOAD_FOLDER'], processed_filename)

        if isinstance(output_image, str) and os.path.exists(output_image):
            shutil.copy(output_image, processed_path)
        elif isinstance(output_image, Image.Image):
            output_image.save(processed_path)
        else:
            with open(processed_path, 'wb') as f:
                f.write(output_image)

        image_url = url_for('uploaded_file', filename=processed_filename, _external=True)

        detections.extend(detection_data)
      
        # กำหนดความมั่นใจขั้นต่ำ
        status = "passed"
        for d in detections:
           # ใช้ thresholds ที่มาจาก api_key_data เพื่อกำหนดค่าความมั่นใจขั้นต่ำ
           threshold = api_key_data['thresholds'].get(d["model_type"], 0.5)
           if d["confidence"] < threshold:
               status = "failed"
               break

        os.remove(file_path)
        threading.Timer(10, delete_file, args=[processed_path]).start()

        if quota != -1:
            api_keys_collection.update_one(
                {"api_key": api_key},
                {"$set": {"quota": quota - 1}}
            )

        return jsonify({
            "status": status,
            "detections": detections,
            "processed_image_url": image_url
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# API สำหรับขอ API Key
@app.route('/request-api-key', methods=['POST'])
def request_api_key():
    data = request.get_json()
    email = data.get('email')
    analysis_types = data.get('analysis_types', [])
    quota = data.get('quota', 100)
    thresholds = data.get('thresholds', {})  # รับค่า thresholds จากฟรอนต์
    plan = data.get('plan', 'free')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    if not analysis_types:
        return jsonify({'error': 'At least one analysis type is required'}), 400

    if plan == 'free':
        existing_free_key = api_keys_collection.find_one({"email": email, "plan": "free"})
        if existing_free_key:
            return jsonify({'error': 'คุณได้ขอ API Key ฟรีไปแล้ว'}), 400

    # สร้าง API Key ใหม่
    api_key = str(uuid.uuid4())

    # บันทึกข้อมูลใหม่
    api_keys_collection.insert_one({
        "email": email,
        "api_key": api_key,
        "analysis_types": analysis_types,
        "thresholds": thresholds,  # บันทึกค่า thresholds
        "quota": quota,
        "plan": plan
    })

    return jsonify({'apiKey': api_key})

# API สำหรับรายงานปัญหา
@app.route('/report-issue', methods=['POST'])
def report_issue():
    issue = request.json.get('issue')
    category = request.json.get('category')
 
    # ล็อกค่า issue และ category เพื่อตรวจสอบ
    print(f"Received issue: {issue}, category: {category}")
 
    if issue and category:
        folder = 'report-issues'
        if not os.path.exists(folder):
            os.makedirs(folder)
 
        # ใช้เวลาปัจจุบันในการตั้งชื่อไฟล์ (formatted)
        filename = f"report-issues/report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
 
        with open(filename, 'w') as file:
            file.write(f"หมวดหมู่: {category}\n")
            file.write(f"รายละเอียดปัญหา: {issue}\n")
       
        return jsonify({'success': True}), 200
    return jsonify({'success': False}), 400
 
# ดูข้อมูล database
@app.route('/get-api-keys', methods=['GET'])
def get_api_keys():
    email = request.args.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    # ตรวจสอบการเชื่อมต่อฐานข้อมูล
    try:
        user = api_keys_collection.find({"email": email})
        api_keys = list(user)  # แปลง cursor เป็น list
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

    if not api_keys:
        return jsonify({'error': 'No API keys found for this email'}), 404

    # ส่งคืนข้อมูล API Keys ทั้งหมดของผู้ใช้ พร้อม threshold
    return jsonify({
        'api_keys': [{
            'api_key': key.get('api_key', 'ไม่พบ API Key'),
            'analysis_types': key.get('analysis_types', []),
            'quota': key.get('quota', 0),
            'thresholds': key.get('thresholds', 0.5)  # เพิ่มตรงนี้ (ค่า default = 0.5 ถ้าไม่มีใน DB)
        } for key in api_keys]
    })


@app.route("/get-username", methods=["GET"])
def get_username():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Missing email parameter"}), 400

    user = users_collection.find_one({"email": email})
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"username": user.get("username")}), 200

# API สำหรับดาวน์โหลดเอกสารคู่มือ
@app.route('/manual')
def download_manual():
    # ระบุเส้นทางไฟล์ PDF ที่เก็บอยู่ใน root directory
    file_path = os.path.join(app.root_path, 'manual.pdf')  # 'manual.pdf' คือชื่อไฟล์
    return send_from_directory(app.root_path, 'manual.pdf')
 
# ให้บริการไฟล์ที่อัปโหลด
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)
 
# API สำหรับสร้าง QR Code
def generate_qr_code(promptpay_id, amount=0):
    # สร้าง payload ด้วยหมายเลข PromptPay และจำนวนเงิน
    if amount > 0:
        payload = qrcode.generate_payload(promptpay_id, amount)
    else:
        payload = qrcode.generate_payload(promptpay_id)
 
    # สร้าง QR Code จาก payload
    img = qrcode.to_image(payload)
 
    # แปลงภาพ QR Code เป็น Base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
 
    return f"data:image/png;base64,{img_str}"
 
# เพิ่มตอนสร้าง QR ให้สร้าง ref_code และบันทึก order
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.get_json()
    amount = float(data.get('amount', 0))
    promptpay_id = data.get('promptpay_id', '66882884744')
    email = data.get('email', '')
    quota = int(data.get('quota', 100))
    plan = data.get('plan', 'paid')
    analysis_types = data.get('analysis_types', []),  # ต้องเป็น list
    thresholds = data.get('thresholds', {})
   

    # เวลาประเทศไทย
    thai_time = datetime.now(ZoneInfo("Asia/Bangkok"))
    current_time = thai_time.strftime('%d/%m/%Y %H:%M:%S')

    # สร้าง UUID และ ref_code
    uuid_value = uuid.uuid4().hex[:10]
    ref_code = f"{current_time} {uuid_value}"

    # บันทึกออร์เดอร์ลงฐานข้อมูล
    orders_collection.insert_one({
        "ref_code": ref_code,
        "email": email,
        "amount": amount,
        "quota": quota,
        "plan": plan,
        "analysis_types": analysis_types,
        "thresholds": thresholds,
        "paid": False,
        "created_at": current_time,                      # เวลาโชว์แบบไทย
        "created_time": datetime.now(timezone.utc)       # สำหรับ TTL index
    })

    # สร้าง QR
    qr_base64 = generate_qr_code(promptpay_id, amount)

    # ส่งกลับ QR + ref_code
    return jsonify({
        "qr_code_url": qr_base64,
        "ref_code": ref_code
    })

# TTL index
orders_collection.create_index(
    [("created_time", 1)],
    expireAfterSeconds=600  # 10 นาที
)
 
# ฟังก์ชันตรวจสอบว่ามี QR Code หรือไม่
def check_qrcode(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return False
    detector = cv2.QRCodeDetector()
    retval, points = detector.detect(image)  # ใช้ detect() แทน detectAndDecode()
   
    if retval:  # ถ้าคืนค่า True แสดงว่ามี QR code ในภาพ
        return True
    return False
 
# ฟังก์ชันตรวจสอบรหัสอ้างอิงและเวลาในสลิป
@app.route('/upload-receipt', methods=['POST'])
def upload_receipt():
    if 'receipt' not in request.files:
        return jsonify({'error': 'No receipt file provided'}), 400
    
    file = request.files['receipt']
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)
    
    if not is_image(save_path):
        os.remove(save_path)
        return jsonify({'error': 'ไฟล์ไม่ใช่รูปภาพ'}), 400
    
    # ตรวจสอบว่าภาพมี QR Code หรือไม่
    if not check_qrcode(save_path):
        os.remove(save_path)
        return jsonify({'error': 'รูปเเบบใบเสร็จไม่ถูกต้อง'}), 400

    client = Client("Phurin1/ocr-receipt")
    result = client.predict(
        image=handle_file(save_path),
        api_name="/predict"
    )
    
    ocr_data = result
    
    # ตรวจสอบข้อมูลที่จำเป็นต้องมี
    required_fields = ['full_text', 'date', 'time', 'uuids', 'amount', 'full_name', 'time_receipts']
    for field in required_fields:
        if not ocr_data.get(field):
            os.remove(save_path)
            return jsonify({'error': f"ข้อมูล {field} ขาดหายไปหรือเป็นค่าว่าง"}), 400
    
    # รับข้อมูลที่ได้จาก OCR
    text = ocr_data['full_text']
    uuid_list = ocr_data['date'] + " " + ocr_data['time'] + " " + " ".join(ocr_data['uuids'])
    date_text = ocr_data['date']
    time = ocr_data['time']
    amount = ocr_data['amount']
    full_name = ocr_data['full_name']
    time_receipts = ocr_data["time_receipts"]
    
    # แสดงค่าของตัวแปรที่ได้รับ
    print("OCR Full Text: ", text)
    print("UUID List: ", uuid_list)
    print("Date from OCR: ", date_text)
    print("Time from OCR: ", time)
    print("Amount from OCR: ", amount)
    print("full_name: ", full_name)
    print("time_receipts: ", time_receipts)
    
    # ตรวจสอบ UUID กับฐานข้อมูล
    matched_order = orders_collection.find_one({"ref_code": uuid_list})
    if not matched_order:
        os.remove(save_path)
        return jsonify({
            'error': 'ไม่พบรหัสอ้างอิงในฐานข้อมูล',
            'ocr_data': {
                'full_text': text,
                'uuids': uuid_list,
                'date': date_text,
                'time': time,
                'amount': amount,
                'fullname': full_name
            }
        }), 404
    
    # ตรวจสอบชื่อ
    full_name = ocr_data.get("full_name", "")
    if "ภูรินทร์สุขมั่น" not in full_name:
        os.remove(save_path)
        return jsonify({'error': 'ชื่อผู้รับเงินไม่ถูกต้อง'}), 400
    
    # ตรวจสอบวันที่
    try:
        created_datetime = datetime.strptime(matched_order["created_at"], '%d/%m/%Y %H:%M:%S')
    except:
        os.remove(save_path)
        return jsonify({'error': 'ข้อมูลวันที่ในฐานข้อมูลผิดพลาด'}), 500
    
    if date_text:
        try:
            date_from_ocr = datetime.strptime(date_text, '%d/%m/%Y').date()
            if date_from_ocr != created_datetime.date():
                os.remove(save_path)
                return jsonify({'error': 'วันที่ในสลิปไม่ตรงกับวันที่สร้างออร์เดอร์'}), 400
        except:
            os.remove(save_path)
            return jsonify({'error': 'รูปแบบวันที่ในสลิปผิด'}), 400
    
    # ตรวจสอบเวลา
    if time_receipts:
        try:
            time_from_ocr = datetime.strptime(time_receipts, '%H:%M')
            time_from_ocr_full = datetime.combine(created_datetime.date(), time_from_ocr.time())
            time_diff = abs((created_datetime - time_from_ocr_full).total_seconds())
            if time_diff > 300:
                os.remove(save_path)
                return jsonify({'error': 'เวลาในสลิปห่างกันเกิน 5 นาที'}), 400
        except:
            os.remove(save_path)
            return jsonify({'error': 'รูปแบบเวลาในสลิปผิด'}), 400
    
    # ตรวจสอบยอดเงิน
    if amount:
        try:
            amount = float(amount.replace(',', ''))
            if float(matched_order.get('amount', 0)) != amount:
                os.remove(save_path)
                return jsonify({'error': 'ยอดเงินไม่ตรงกัน'}), 400
        except:
            os.remove(save_path)
            return jsonify({'error': 'ยอดเงินไม่สามารถแปลงได้'}), 400
    
    # สร้าง API Key และอัปเดตสถานะการชำระเงิน
    orders_collection.update_one({"_id": matched_order["_id"]}, {
        "$set": {"paid": True, "paid_at": datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    })
    
    api_key = str(uuid.uuid4())
    api_keys_collection.insert_one({
        "email": matched_order.get('email', ''),
        "api_key": api_key,
        "analysis_types": matched_order.get('analysis_types', []),
        "thresholds": matched_order.get('thresholds', {}),
        "quota": matched_order.get('quota', 100),
        "plan": matched_order.get('plan', 'paid'),
        "created_at": datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    })
    
    # ลบออร์เดอร์ออกจากฐานข้อมูลหลังจากสร้าง API Key แล้ว
    orders_collection.delete_one({"ref_code": uuid_list})
    os.remove(save_path)
    
    return jsonify({
        'success': True,
        'message': 'อัปโหลดสำเร็จ',
        'api_key': api_key,
        'ocr_data': {
            'uuids': uuid_list,
            'date': date_text,
            'time': time,
            'amount': amount,
            'fullname': full_name,
            'full_text': text,
        }
    }), 200
 
@app.route('/auth/google')
def auth_google():
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid email profile"
    )
    return redirect(google_auth_url)
 
@app.route('/auth/google/callback')
def google_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'Authorization code not found'}), 400
 
    # แลกเปลี่ยน code เป็น access token
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    token_response = requests.post(token_url, data=token_data)
    token_json = token_response.json()
 
    access_token = token_json.get('access_token')
    id_token = token_json.get('id_token')
 
    # ดึงข้อมูลโปรไฟล์ผู้ใช้
    user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    user_info_response = requests.get(user_info_url, headers={'Authorization': f'Bearer {access_token}'})
    user_info = user_info_response.json()
 
    # ตรวจสอบว่าผู้ใช้อยู่ในระบบหรือยัง
    email = user_info.get('email')
    user = users_collection.find_one({"email": email})
    if not user:
        # หากผู้ใช้ยังไม่มีในระบบ ให้เพิ่มเข้าไป
        users_collection.insert_one({
            "email": email,
            "username": user_info.get('name'),
            "password": None  # ไม่มีรหัสผ่านเพราะล็อกอินด้วย Google
        })
 
    # เปลี่ยนเส้นทางไปยัง plan.html
    return redirect(f'/apikey/view-api-keys.html?email={email}')
 
# สร้าง OTP และส่งอีเมล
@app.route('/reset-request', methods=['POST'])
def reset_request():
    email = request.json.get('email')
    if not users_collection.find_one({'email': email}):
        return jsonify({'message': 'ไม่พบอีเมลนี้'}), 404
 
    otp = str(random.randint(100000, 999999))
    expiration = datetime.utcnow() + timedelta(minutes=5)
 
    otp_collection.update_one(
        {'email': email},
        {'$set': {'otp': otp, 'otp_expiration': expiration, 'used': False}},
        upsert=True
    )
 
    msg = Message('OTP สำหรับรีเซ็ตรหัสผ่าน', recipients=[email])
    msg.body = f'รหัส OTP ของคุณคือ: {otp}'
    mail.send(msg)
 
    return jsonify({'message': 'ส่ง OTP แล้ว'}), 200
 
# ตรวจสอบ OTP
@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')
 
    record = otp_collection.find_one({'email': email, 'otp': otp, 'used': False})
    if not record:
        return jsonify({'message': 'OTP ไม่ถูกต้อง'}), 400
 
    if record['otp_expiration'] < datetime.utcnow():
        return jsonify({'message': 'OTP หมดอายุแล้ว'}), 400
 
    return jsonify({'message': 'OTP ถูกต้อง'}), 200
 
# ตั้งรหัสผ่านใหม่
@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
 
    if password != confirm_password:
        return jsonify({'message': 'รหัสผ่านไม่ตรงกัน'}), 400
 
    record = otp_collection.find_one({'email': email, 'otp': otp, 'used': False})
    if not record or record['otp_expiration'] < datetime.utcnow():
        return jsonify({'message': 'OTP ไม่ถูกต้องหรือหมดอายุ'}), 400
 
    # แฮชรหัสผ่านใหม่ก่อนอัปเดตในฐานข้อมูล
    hashed_password = generate_password_hash(password, method="pbkdf2:sha256", salt_length=8)
 
    users_collection.update_one({'email': email}, {'$set': {'password': hashed_password}})
    otp_collection.update_one({'email': email}, {'$set': {'used': True}})
 
    return jsonify({'message': 'รีเซ็ตรหัสผ่านเรียบร้อยแล้ว'}), 200
 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)