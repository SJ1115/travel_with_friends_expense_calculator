# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os

app = Flask(__name__)

# 데이터 저장용 전역 변수 (실제 운영에서는 데이터베이스 사용 권장)
data = {
    'people': [],
    'expenses': [],
    'exchange_rates': {
        'JPY': None,
        'USD': None,
        'EUR': None,
        'CNY': None
    }
}

# 데이터 파일 저장/로드
DATA_FILE = 'expense_data.json'

def load_data():
    global data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            pass

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def calculate_settlement():
    """정산 계산 (모든 금액을 원화로 환산)"""
    if not data['people'] or not data['expenses']:
        return {}
    
    balances = {person: 0 for person in data['people']}
    
    for expense in data['expenses']:
        amount = expense['amount']
        currency = expense.get('currency', 'JPY')
        payer = expense['payer']
        participants = expense['participants']
        
        # 원화로 환산
        if currency == 'KRW':
            krw_amount = amount
        else:
            exchange_rate = data['exchange_rates'].get(currency)
            if exchange_rate:
                krw_amount = amount * exchange_rate
            else:
                krw_amount = amount  # 환율이 없으면 그대로 사용
        
        share_per_person = krw_amount / len(participants)
        
        balances[payer] += krw_amount
        
        for participant in participants:
            balances[participant] -= share_per_person
    
    return balances

@app.route('/')
def index():
    load_data()
    balances = calculate_settlement()
    
    # 총 지출 계산 (원화 기준)
    total_expense_krw = 0
    total_by_currency = {'KRW': 0, 'JPY': 0, 'USD': 0, 'EUR': 0, 'CNY': 0}
    
    for exp in data['expenses']:
        currency = exp.get('currency', 'JPY')
        amount = exp['amount']
        total_by_currency[currency] += amount
        
        # 원화로 환산
        if currency == 'KRW':
            total_expense_krw += amount
        else:
            exchange_rate = data['exchange_rates'].get(currency)
            if exchange_rate:
                total_expense_krw += amount * exchange_rate
            else:
                total_expense_krw += amount
    
    return render_template('index.html', 
                         data=data, 
                         balances=balances, 
                         total_expense_krw=total_expense_krw,
                         total_by_currency=total_by_currency)

@app.route('/add_person', methods=['POST'])
def add_person():
    name = request.form.get('name', '').strip()
    if name and name not in data['people']:
        data['people'].append(name)
        save_data()
    return redirect(url_for('index'))

@app.route('/remove_person/<name>')
def remove_person(name):
    if name in data['people'] and len(data['people']) > 1:
        data['people'].remove(name)
        # 해당 사람 관련 지출도 제거
        data['expenses'] = [exp for exp in data['expenses'] 
                          if exp['payer'] != name and name not in exp['participants']]
        save_data()
    return redirect(url_for('index'))

@app.route('/add_expense', methods=['POST'])
def add_expense():
    description = request.form.get('description', '').strip()
    amount = request.form.get('amount', '')
    currency = request.form.get('currency', 'JPY')
    payer = request.form.get('payer', '')
    participants = request.form.getlist('participants')
    
    if description and amount and payer:
        try:
            amount = float(amount)
            if not participants:
                participants = data['people'].copy()
            
            # 유효한 참가자만 필터링
            participants = [p for p in participants if p in data['people']]
            
            if participants:
                expense = {
                    'id': len(data['expenses']) + 1,
                    'description': description,
                    'amount': amount,
                    'currency': currency,
                    'payer': payer,
                    'participants': participants
                }
                data['expenses'].append(expense)
                save_data()
        except ValueError:
            pass
    
    return redirect(url_for('index'))

@app.route('/remove_expense/<int:expense_id>')
def remove_expense(expense_id):
    data['expenses'] = [exp for exp in data['expenses'] if exp['id'] != expense_id]
    save_data()
    return redirect(url_for('index'))

@app.route('/set_exchange_rate', methods=['POST'])
def set_exchange_rate():
    for currency in ['JPY', 'USD', 'EUR', 'CNY']:
        rate = request.form.get(f'rate_{currency}', '')
        if rate:
            try:
                data['exchange_rates'][currency] = float(rate)
            except ValueError:
                data['exchange_rates'][currency] = None
        else:
            data['exchange_rates'][currency] = None
    
    save_data()
    return redirect(url_for('index'))

@app.route('/clear_all', methods=['POST'])
def clear_all():
    data['people'] = []
    data['expenses'] = []
    data['exchange_rates'] = {
        'JPY': None,
        'USD': None,
        'EUR': None,
        'CNY': None
    }
    save_data()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # templates 폴더 생성
    os.makedirs('templates', exist_ok=True)
    
    # HTML 템플릿 생성
    html_template = '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>여행 경비 정산</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            padding: 30px;
        }
        
        .section {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .section h2 {
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #4CAF50;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        
        .form-group input, .form-group select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #4CAF50;
            box-shadow: 0 0 5px rgba(76, 175, 80, 0.3);
        }
        
        .btn {
            background: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        
        .btn:hover {
            background: #45a049;
        }
        
        .btn-danger {
            background: #f44336;
        }
        
        .btn-danger:hover {
            background: #da190b;
        }
        
        .btn-warning {
            background: #ff9800;
        }
        
        .btn-warning:hover {
            background: #e68900;
        }
        
        .btn-small {
            padding: 5px 10px;
            font-size: 12px;
            margin-left: 5px;
        }
        
        .scroll-list {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            background: white;
        }
        
        .list-item {
            padding: 10px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .list-item:last-child {
            border-bottom: none;
        }
        
        .list-item:hover {
            background: #f5f5f5;
        }
        
        .person-tag {
            display: inline-block;
            background: #e3f2fd;
            color: #1976d2;
            padding: 3px 8px;
            border-radius: 15px;
            font-size: 12px;
            margin: 2px;
        }
        
        .expense-details {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
        
        .settlement-section {
            grid-column: 1 / -1;
            margin-top: 20px;
        }
        
        .settlement-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .settlement-card {
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            font-weight: bold;
        }
        
        .settlement-positive {
            background: #e8f5e8;
            border: 2px solid #4CAF50;
            color: #2e7d32;
        }
        
        .settlement-negative {
            background: #ffebee;
            border: 2px solid #f44336;
            color: #c62828;
        }
        
        .settlement-zero {
            background: #f5f5f5;
            border: 2px solid #9e9e9e;
            color: #666;
        }
        
        .checkbox-group {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 10px;
        }
        
        .checkbox-item {
            display: flex;
            align-items: center;
            background: #f0f0f0;
            padding: 5px 10px;
            border-radius: 15px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .checkbox-item:hover {
            background: #e0e0e0;
        }
        
        .checkbox-item input {
            margin-right: 5px;
            width: auto;
        }
        
        .total-info {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            text-align: center;
        }
        
        .clear-section {
            text-align: center;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }
        
        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
            }
            
            .settlement-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎒 여행 경비 정산</h1>
            <p>여행 비용을 쉽게 관리하고 공평하게 정산하세요</p>
        </div>
        
        <div class="main-content">
            <!-- 참가자 관리 -->
            <div class="section">
                <h2>👥 참가자 관리</h2>
                <form method="POST" action="/add_person">
                    <div class="form-group">
                        <label>새 참가자</label>
                        <div style="display: flex; gap: 10px;">
                            <input type="text" name="name" placeholder="이름을 입력하세요" required>
                            <button type="submit" class="btn">추가</button>
                        </div>
                    </div>
                </form>
                
                <div class="scroll-list">
                    {% if data.people %}
                        {% for person in data.people %}
                        <div class="list-item">
                            <span>{{ person }}</span>
                            {% if data.people|length > 1 %}
                            <a href="/remove_person/{{ person }}" class="btn btn-danger btn-small" 
                               onclick="return confirm('{{ person }}님을 삭제하시겠습니까?')">삭제</a>
                            {% endif %}
                        </div>
                        {% endfor %}
                    {% else %}
                        <div class="list-item">참가자가 없습니다.</div>
                    {% endif %}
                </div>
            </div>
            
            <!-- 지출 입력 -->
            <div class="section">
                <h2>💰 지출 입력</h2>
                {% if data.people %}
                <form method="POST" action="/add_expense">
                    <div class="form-group">
                        <label>지출 항목</label>
                        <input type="text" name="description" placeholder="예: 점심식사" required>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 10px;">
                        <div class="form-group">
                            <label>금액</label>
                            <input type="number" name="amount" placeholder="0" min="0" step="0.01" required>
                        </div>
                        
                        <div class="form-group">
                            <label>통화</label>
                            <select name="currency">
                                <option value="JPY" selected>JPY (엔)</option>
                                <option value="KRW">KRW (원)</option>
                                <option value="USD">USD (달러)</option>
                                <option value="EUR">EUR (유로)</option>
                                <option value="CNY">CNY (위안)</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>지불자</label>
                        <select name="payer" required>
                            <option value="">선택하세요</option>
                            {% for person in data.people %}
                            <option value="{{ person }}">{{ person }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>참가자 (선택안하면 전체 적용)</label>
                        <div class="checkbox-group">
                            {% for person in data.people %}
                            <label class="checkbox-item">
                                <input type="checkbox" name="participants" value="{{ person }}">
                                {{ person }}
                            </label>
                            {% endfor %}
                        </div>
                    </div>
                    
                    <button type="submit" class="btn">지출 추가</button>
                </form>
                {% else %}
                <p>먼저 참가자를 추가하세요.</p>
                {% endif %}
            </div>
            
            <!-- 지출 내역 -->
            <div class="section">
                <h2>📋 지출 내역</h2>
                <div class="scroll-list">
                    {% if data.expenses %}
                        {% for expense in data.expenses %}
                        <div class="list-item">
                            <div>
                                <strong>{{ expense.description }}</strong>
                                <div class="expense-details">
                                    💰 {{ "{:,}".format(expense.amount|int) }} {{ expense.get('currency', 'JPY') }} ({{ expense.payer }}가 지불)
                                    {% if expense.get('currency', 'JPY') != 'KRW' and data.exchange_rates.get(expense.get('currency', 'JPY')) %}
                                        <br>💱 원화 환산: {{ "{:,}".format((expense.amount * data.exchange_rates.get(expense.get('currency', 'JPY'), 1))|int) }}원
                                    {% endif %}
                                    <br>
                                    👥 참가자: 
                                    {% for participant in expense.participants %}
                                        <span class="person-tag">{{ participant }}</span>
                                    {% endfor %}
                                    <br>
                                    📊 1인당: 
                                    {% if expense.get('currency', 'JPY') == 'KRW' %}
                                        {{ "{:,}".format((expense.amount / expense.participants|length)|int) }}원
                                    {% else %}
                                        {% if data.exchange_rates.get(expense.get('currency', 'JPY')) %}
                                            {{ "{:,}".format((expense.amount * data.exchange_rates.get(expense.get('currency', 'JPY'), 1) / expense.participants|length)|int) }}원
                                        {% else %}
                                            {{ "{:,}".format((expense.amount / expense.participants|length)|int) }} {{ expense.get('currency', 'JPY') }}
                                        {% endif %}
                                    {% endif %}
                                </div>
                            </div>
                            <a href="/remove_expense/{{ expense.id }}" class="btn btn-danger btn-small"
                               onclick="return confirm('이 지출을 삭제하시겠습니까?')">삭제</a>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div class="list-item">지출 내역이 없습니다.</div>
                    {% endif %}
                </div>
            </div>
            
            <!-- 환율 설정 -->
            <div class="section">
                <h2>💱 환율 설정</h2>
                <form method="POST" action="/set_exchange_rate">
                    <p class="form-group" style="margin-bottom: 20px; color: #666; font-size: 14px;">
                        외화를 원화로 환산하기 위한 환율을 설정하세요 (1 외화 = ? 원)
                    </p>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="form-group">
                            <label>JPY (엔)</label>
                            <input type="number" name="rate_JPY" step="0.01" 
                                   value="{{ data.exchange_rates.JPY if data.exchange_rates.JPY else '' }}"
                                   placeholder="예: 9.2">
                        </div>
                        
                        <div class="form-group">
                            <label>USD (달러)</label>
                            <input type="number" name="rate_USD" step="0.01" 
                                   value="{{ data.exchange_rates.USD if data.exchange_rates.USD else '' }}"
                                   placeholder="예: 1350">
                        </div>
                        
                        <div class="form-group">
                            <label>EUR (유로)</label>
                            <input type="number" name="rate_EUR" step="0.01" 
                                   value="{{ data.exchange_rates.EUR if data.exchange_rates.EUR else '' }}"
                                   placeholder="예: 1450">
                        </div>
                        
                        <div class="form-group">
                            <label>CNY (위안)</label>
                            <input type="number" name="rate_CNY" step="0.01" 
                                   value="{{ data.exchange_rates.CNY if data.exchange_rates.CNY else '' }}"
                                   placeholder="예: 190">
                        </div>
                    </div>
                    
                    <button type="submit" class="btn">환율 저장</button>
                </form>
            </div>
            
            <!-- 정산 결과 -->
            {% if data.expenses and balances %}
            <div class="section settlement-section">
                <h2>💰 정산 결과 (원화 기준)</h2>
                
                <div class="total-info">
                    <h3>📊 총 지출 요약</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 15px 0;">
                        {% for currency, amount in total_by_currency.items() %}
                            {% if amount > 0 %}
                            <div style="background: white; padding: 10px; border-radius: 5px; text-align: center;">
                                <strong>{{ currency }}</strong><br>
                                {{ "{:,}".format(amount|int) }}
                                {% if currency != 'KRW' and data.exchange_rates.get(currency) %}
                                    <br><small>({{ "{:,}".format((amount * data.exchange_rates.get(currency))|int) }}원)</small>
                                {% endif %}
                            </div>
                            {% endif %}
                        {% endfor %}
                    </div>
                    <h3 style="color: #4CAF50;">🧮 총계: {{ "{:,}".format(total_expense_krw|int) }}원</h3>
                </div>
                
                <div class="settlement-grid">
                    {% for person, balance in balances.items() %}
                    <div class="settlement-card 
                        {% if balance > 0 %}settlement-positive
                        {% elif balance < 0 %}settlement-negative
                        {% else %}settlement-zero{% endif %}">
                        <h3>{{ person }}</h3>
                        {% if balance > 0 %}
                            <p>💚 받을 금액</p>
                            <p style="font-size: 1.2em;">{{ "{:,}".format(balance|int) }}원</p>
                        {% elif balance < 0 %}
                            <p>💸 낼 금액</p>
                            <p style="font-size: 1.2em;">{{ "{:,}".format((-balance)|int) }}원</p>
                        {% else %}
                            <p>⚖️ 정산 완료</p>
                            <p style="font-size: 1.2em;">0원</p>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        </div>
        
        <!-- 전체 초기화 -->
        {% if data.people or data.expenses %}
        <div class="clear-section">
            <form method="POST" action="/clear_all" 
                  onsubmit="return confirm('모든 데이터를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')">
                <button type="submit" class="btn btn-warning">🗑️ 전체 초기화</button>
            </form>
        </div>
        {% endif %}
    </div>
</body>
</html>'''
    
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print("🎒 여행 경비 정산 웹앱을 시작합니다!")
    print("📱 브라우저에서 http://localhost:5000 으로 접속하세요")
    print("🛑 종료하려면 Ctrl+C를 누르세요")
    
    app.run(debug=True, host='0.0.0.0', port=5000)