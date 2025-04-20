from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from PIL import Image
import os
import base64
import json
from datetime import datetime
import io
import logging

app = Flask(__name__, static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 設定最大上傳檔案大小為 16MB
CORS(app, resources={
    r"/*": {
        "origins": "*",  # 允許所有來源
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
    }
})

# 設定日誌
logging.basicConfig(level=logging.DEBUG)

# 取得 Render 的 PORT 環境變數，如果沒有就使用 5000
PORT = int(os.environ.get('PORT', 5000))

# 設定上傳文件夾
UPLOAD_FOLDER = 'uploads'
MUSIC_FOLDER = 'uploads/music'

# 確保上傳目錄存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MUSIC_FOLDER, exist_ok=True)

# 設定允許的文件類型
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_MUSIC_EXTENSIONS = {'mp3', 'wav'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def root():
    return send_file('card.html')

@app.route('/card.html')
def serve_card():
    return send_file('card.html')

@app.route('/api/save_card', methods=['POST'])
def save_card():
    try:
        data = request.get_json()
        if not data:
            app.logger.error('無效的請求數據')
            return jsonify({'success': False, 'message': '無效的請求數據'}), 400

        card_id = str(datetime.now().timestamp())
        
        # 保存卡片數據
        card_data_path = os.path.join(UPLOAD_FOLDER, f'card_{card_id}.json')
        with open(card_data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        response = jsonify({
            'success': True,
            'card_id': card_id,
            'message': '卡片保存成功'
        })
        
        return response

    except Exception as e:
        app.logger.error(f'保存卡片時發生錯誤: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'保存失敗: {str(e)}'
        }), 500

@app.route('/api/load_card/<card_id>')
def load_card(card_id):
    try:
        card_data_path = os.path.join(UPLOAD_FOLDER, f'card_{card_id}.json')
        if not os.path.exists(card_data_path):
            app.logger.error(f'找不到卡片文件: {card_data_path}')
            return jsonify({
                'success': False,
                'message': '找不到卡片'
            }), 404
            
        with open(card_data_path, 'r', encoding='utf-8') as f:
            card_data = json.load(f)
            
        return jsonify({
            'success': True,
            'data': card_data
        })
    except Exception as e:
        app.logger.error(f'讀取卡片時發生錯誤: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'讀取失敗: {str(e)}'
        }), 500

@app.route('/api/upload_photo', methods=['POST'])
def upload_photo():
    try:
        if 'photo' not in request.files:
            app.logger.error('沒有上傳文件')
            return jsonify({
                'success': False,
                'message': '沒有上傳文件'
            }), 400
            
        file = request.files['photo']
        if file.filename == '':
            app.logger.error('沒有選擇文件')
            return jsonify({
                'success': False,
                'message': '沒有選擇文件'
            }), 400
            
        if file and allowed_file(file.filename, ALLOWED_EXTENSIONS):
            # 生成唯一文件名
            filename = f"{datetime.now().timestamp()}_{file.filename}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # 打開並處理圖片
            image = Image.open(file)
            
            # 計算適當的尺寸
            target_width = 800
            target_height = 450  # 16:9 比例
            
            # 計算縮放比例
            width_ratio = target_width / image.width
            height_ratio = target_height / image.height
            
            # 選擇較小的比例來確保圖片完全顯示
            ratio = min(width_ratio, height_ratio)
            
            # 計算新尺寸
            new_width = int(image.width * ratio)
            new_height = int(image.height * ratio)
            
            # 使用 LANCZOS 重採樣方法來調整圖片大小
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 創建新的白色背景圖片
            background = Image.new('RGB', (target_width, target_height), (245, 245, 245))
            
            # 計算圖片在背景中的位置（置中）
            x = (target_width - new_width) // 2
            y = (target_height - new_height) // 2
            
            # 將調整大小後的圖片貼到背景上
            background.paste(image, (x, y))
            
            # 保存並壓縮圖片
            background.save(filepath, 
                          optimize=True, 
                          quality=85,
                          format=image.format if image.format else 'JPEG')
            
            return jsonify({
                'success': True,
                'filename': filename,
                'url': f'/uploads/{filename}'
            })
    except Exception as e:
        app.logger.error(f'上傳照片時發生錯誤: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'上傳失敗: {str(e)}'
        }), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/upload_music', methods=['POST'])
def upload_music():
    try:
        if 'music' not in request.files:
            app.logger.error('沒有上傳音樂文件')
            return jsonify({
                'success': False,
                'message': '沒有上傳音樂文件'
            }), 400
            
        file = request.files['music']
        if file.filename == '':
            app.logger.error('沒有選擇文件')
            return jsonify({
                'success': False,
                'message': '沒有選擇文件'
            }), 400
            
        if file and allowed_file(file.filename, ALLOWED_MUSIC_EXTENSIONS):
            filename = f"{datetime.now().timestamp()}_{file.filename}"
            filepath = os.path.join(MUSIC_FOLDER, filename)
            file.save(filepath)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'url': f'/music/{filename}'
            })
    except Exception as e:
        app.logger.error(f'上傳音樂時發生錯誤: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'上傳失敗: {str(e)}'
        }), 500

@app.route('/music/<filename>')
def get_music(filename):
    return send_from_directory(MUSIC_FOLDER, filename)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

if __name__ == '__main__':
    # 在本地開發時使用 debug 模式
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=PORT, debug=debug_mode)