from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = 'Jack1234@12'

# PostgreSQL DB config
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://postgresql:12345@host:5432/orders_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
from dotenv import load_dotenv  # Load local .env for development
load_dotenv()
app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key')

# Flask-Mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'jacktyler471@gmail.com'
app.config['MAIL_PASSWORD'] = 'wtgb elhj fdjy syzg'
app.config['MAIL_DEFAULT_SENDER'] = 'your_email@gmail.com'

db = SQLAlchemy(app)
mail = Mail(app)
s = URLSafeTimedSerializer(app.secret_key)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    food_item = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    position = db.Column(db.Integer)
    emoji = db.Column(db.String(50))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    food_item = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(255), nullable=False)

# Admin-only decorator
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_logged_in') or not session.get('is_admin'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# Routes
@app.route('/')
def home():
    return render_template('home.html', user_logged_in=session.get('user_logged_in'), username=session.get('username'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter((User.username == username) | (User.email == email)).first():
            return "Username or email already exists."

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        token = s.dumps(email, salt='email-confirm')
        verify_url = url_for('verify_email', token=token, _external=True)
        msg = Message('Welcome to Neon Food Express - Verify Your Email', recipients=[email])
        msg.html = render_template('email_verification.html', username=username, verification_link=verify_url)
        mail.send(msg)

        return render_template('email_verification_sent.html', email=email, username=username)

    return render_template('signup.html', user_logged_in=session.get('user_logged_in'), username=session.get('username'))

@app.route('/verify-email/<token>')
def verify_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except Exception:
        return render_template('verification_result.html', status='error', message='The confirmation link is invalid or has expired.')

    user = User.query.filter_by(email=email).first()
    if user:
        user.is_verified = True
        db.session.commit()
        return render_template('verification_result.html', status='success', message='Your email has been successfully verified! You can now login.')
    return render_template('verification_result.html', status='error', message='User not found. Please sign up again.')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['username']
        password = request.form['password']

        user = User.query.filter(
            ((User.username == username_or_email) | (User.email == username_or_email)) &
            (User.password == password)
        ).first()

        if user:
            if not user.is_verified:
                return 'Please verify your email before logging in.'
            session['user_logged_in'] = True
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            return redirect(url_for('dashboard' if user.is_admin else 'home'))
        return "Invalid credentials. Please try again."

    return render_template('login.html', user_logged_in=session.get('user_logged_in'), username=session.get('username'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            return render_template('forgot_password.html', error="Please enter your email address.")
        user = User.query.filter_by(email=email).first()
        if user:
            token = s.dumps(email, salt='reset-password')
            reset_url = url_for('reset_password', token=token, _external=True)
            msg = Message('Password Reset Request', recipients=[email])
            msg.html = render_template('password_reset_email.html', username=user.username, reset_url=reset_url)
            mail.send(msg)
            return render_template('password_reset_sent.html', email=email, username=user.username)
        return render_template('password_reset_sent.html', email=email, username=None, error=True)
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='reset-password', max_age=3600)
    except Exception:
        return render_template('reset_password_error.html', message="The reset link is invalid or has expired.")
    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        if not new_password:
            return render_template('reset_password.html', error="Please enter a new password.")
        user = User.query.filter_by(email=email).first()
        if user:
            user.password = new_password
            db.session.commit()
            return redirect(url_for('login'))
        return render_template('reset_password_error.html', message="User not found.")
    return render_template('reset_password.html')

@app.route('/dashboard')
@admin_required
def dashboard():
    total_users = User.query.count()
    total_orders = Order.query.count()
    top_result = db.session.query(Order.food_item, db.func.sum(Order.quantity).label('total')).group_by(Order.food_item).order_by(db.desc('total')).first()
    top_item = top_result.food_item if top_result else "N/A"
    recent_orders = db.session.query(Order.username, Order.food_item, Order.quantity).order_by(Order.id.desc()).limit(10).all()
    chart_data = db.session.query(Order.food_item, db.func.sum(Order.quantity).label('total')).group_by(Order.food_item).all()
    chart_labels = [row.food_item for row in chart_data]
    chart_values = [row.total for row in chart_data]
    return render_template('dashboard.html', user_logged_in=True, username=session.get('username'), total_users=total_users, total_orders=total_orders, top_item=top_item, recent_orders=recent_orders, chart_labels=chart_labels, chart_values=chart_values)

@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin():
    message = None
    if request.method == 'POST':
        item = request.form['new_item']
        emoji = request.form.get('emoji', '')
        price = float(request.form['price'])
        category = request.form['category']
        position = int(request.form['position'])
        description = request.form.get('description', '')
        new_menu = Menu(food_item=item, category=category, price=price, description=description, position=position, emoji=emoji)
        db.session.add(new_menu)
        db.session.commit()
        message = "✅ Menu updated successfully."
    menu_items = Menu.query.order_by(Menu.category, Menu.position).all()
    return render_template('admin.html', menu_items=menu_items, message=message, user_logged_in=session.get('user_logged_in'), username=session.get('username'))

@app.route('/delete-menu/<int:menu_id>', methods=['POST', 'GET'])
@admin_required
def delete_menu(menu_id):
    Menu.query.filter_by(id=menu_id).delete()
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/about')
def about():
    return render_template('about.html', user_logged_in=session.get('user_logged_in'), username=session.get('username'))

@app.route('/contact')
def contact():
    return render_template('contact.html', user_logged_in=session.get('user_logged_in'), username=session.get('username'))

@app.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        item = request.form['food_item']
        qty = int(request.form['quantity'])
        username = session.get('username')
        new_order = Order(food_item=item, quantity=qty, username=username)
        db.session.add(new_order)
        db.session.commit()
        return redirect(url_for('thankyou'))
    food_items = Menu.query.filter_by(category='regular').order_by(Menu.position).all()
    dessert_items = Menu.query.filter_by(category='dessert').order_by(Menu.position).all()
    combo_items = Menu.query.filter_by(category='combo').order_by(Menu.position).all()
    dessert_combos = Menu.query.filter_by(category='dessert-combo').order_by(Menu.position).all()
    return render_template('index.html', food_items=food_items, dessert_items=dessert_items, combo_items=combo_items, dessert_combos=dessert_combos, user_logged_in=session.get('user_logged_in'), username=session.get('username'))

@app.route('/bulk_order', methods=['POST'])
def bulk_order():
    if not session.get('user_logged_in'):
        return redirect(url_for('login'))
    items = request.form.getlist('items')
    username = session.get('username')
    for item in items:
        try:
            name, qty = item.split(':')
            new_order = Order(food_item=name.strip(), quantity=int(qty), username=username)
            db.session.add(new_order)
        except ValueError:
            continue
    db.session.commit()
    return redirect(url_for('thankyou', ordered='yes'))

@app.route('/orders')
def orders():
    if not session.get('user_logged_in'):
        return redirect(url_for('login'))
    orders = db.session.query(Order.food_item, Order.quantity, Menu.price).join(Menu, Order.food_item == Menu.food_item).filter(Order.username == session.get('username')).all()
    return render_template('orders.html', orders=orders, user_logged_in=True, username=session.get('username'))

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html', user_logged_in=session.get('user_logged_in'), username=session.get('username'))

# Create tables & admin user once on start
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', email='admin@neonfood.com', password='admin123', is_verified=True, is_admin=True)
        db.session.add(admin_user)
        db.session.commit()

# Local dev server (not needed for Render/Heroku)
if __name__ == '__main__':
    app.run(debug=True, port=5090)









