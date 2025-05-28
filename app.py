from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'Jack1234@12'


def init_db():
    with sqlite3.connect('orders.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                food_item TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                description TEXT,
                position INTEGER,
                emoji TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                food_item TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                username TEXT NOT NULL
            )
        ''')


@app.route('/')
def home():
    return render_template('home.html',
                           user_logged_in=session.get('user_logged_in'),
                           username=session.get('username'))


@app.route('/about')
def about():
    return render_template('about.html',
                           user_logged_in=session.get('user_logged_in'),
                           username=session.get('username'))


@app.route('/contact')
def contact():
    return render_template('contact.html',
                           user_logged_in=session.get('user_logged_in'),
                           username=session.get('username'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        try:
            with sqlite3.connect('orders.db') as conn:
                conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                             (username, email, password))
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username or email already exists."
    return render_template('signup.html',
                           user_logged_in=session.get('user_logged_in'),
                           username=session.get('username'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['username']
        password = request.form['password']
        with sqlite3.connect('orders.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT username FROM users
                WHERE (username = ? OR email = ?) AND password = ?
            ''', (username_or_email, username_or_email, password))
            user = cursor.fetchone()
        if user:
            session['user_logged_in'] = True
            session['username'] = user[0]
            return redirect(url_for('home'))
        return "Invalid credentials. Please try again."
    return render_template('login.html',
                           user_logged_in=session.get('user_logged_in'),
                           username=session.get('username'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    message = None
    if request.method == 'POST':
        item = request.form['new_item']
        emoji = request.form.get('emoji', '')
        price = float(request.form['price'])
        category = request.form['category']
        position = int(request.form['position'])
        description = request.form.get('description', '')

        with sqlite3.connect('orders.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO menu (food_item, category, price, description, position, emoji)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (item, category, price, description, position, emoji))
            message = "✅ Menu updated successfully."

    with sqlite3.connect('orders.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, food_item, category, price, description, position, emoji
            FROM menu ORDER BY category, position
        ''')
        menu_items = cursor.fetchall()

    return render_template('admin.html',
                           menu_items=menu_items,
                           message=message,
                           user_logged_in=session.get('user_logged_in'),
                           username=session.get('username'))


@app.route('/delete-menu/<int:menu_id>', methods=['POST', 'GET'])
def delete_menu(menu_id):
    with sqlite3.connect('orders.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM menu WHERE id = ?", (menu_id,))
    return redirect(url_for('admin'))


@app.route('/dashboard')
def dashboard():
    with sqlite3.connect('orders.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM orders')
        total_orders = cursor.fetchone()[0]

        cursor.execute('''
            SELECT food_item, SUM(quantity) AS total
            FROM orders GROUP BY food_item ORDER BY total DESC LIMIT 1
        ''')
        top_result = cursor.fetchone()
        top_item = top_result[0] if top_result else "N/A"

        cursor.execute('''
            SELECT username, food_item, quantity
            FROM orders ORDER BY id DESC LIMIT 10
        ''')
        recent_orders = [dict(username=u, food_item=f, quantity=q) for u, f, q in cursor.fetchall()]

        cursor.execute('''
            SELECT food_item, SUM(quantity) AS total FROM orders GROUP BY food_item
        ''')
        chart_data_raw = cursor.fetchall()
        chart_labels = [row[0] for row in chart_data_raw]
        chart_data = [row[1] for row in chart_data_raw]

    return render_template('dashboard.html',
                           total_users=total_users,
                           total_orders=total_orders,
                           top_item=top_item,
                           recent_orders=recent_orders,
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           user_logged_in=session.get('user_logged_in'),
                           username=session.get('username'))


@app.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        item = request.form['food_item']
        qty = int(request.form['quantity'])
        username = session.get('username')
        with sqlite3.connect('orders.db') as conn:
            conn.execute('''
                INSERT INTO orders (food_item, quantity, username) VALUES (?, ?, ?)
            ''', (item, qty, username))
        return redirect(url_for('thankyou'))

    with sqlite3.connect('orders.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT food_item, price, description, emoji FROM menu WHERE category='regular' ORDER BY position")
        food_items = cursor.fetchall()
        cursor.execute("SELECT food_item, price, description, emoji FROM menu WHERE category='dessert' ORDER BY position")
        dessert_items = cursor.fetchall()
        cursor.execute("SELECT food_item, price, description, emoji FROM menu WHERE category='combo' ORDER BY position")
        combo_items = cursor.fetchall()
        cursor.execute("SELECT food_item, price, description, emoji FROM menu WHERE category='dessert-combo' ORDER BY position")
        dessert_combos = cursor.fetchall()

    return render_template('index.html',
                           food_items=food_items,
                           dessert_items=dessert_items,
                           combo_items=combo_items,
                           dessert_combos=dessert_combos,
                           user_logged_in=session.get('user_logged_in'),
                           username=session.get('username'))


@app.route('/orders')
def orders():
    if not session.get('user_logged_in'):
        return redirect(url_for('login'))

    with sqlite3.connect('orders.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT orders.food_item, orders.quantity, menu.price
            FROM orders
            JOIN menu ON orders.food_item = menu.food_item
            WHERE orders.username = ?
        ''', (session.get('username'),))
        orders = cursor.fetchall()

    return render_template('orders.html',
                           orders=orders,
                           user_logged_in=True,
                           username=session.get('username'))


@app.route('/bulk_order', methods=['POST'])
def bulk_order():
    items = request.form.getlist('items')
    username = session.get('username')

    with sqlite3.connect('orders.db') as conn:
        cursor = conn.cursor()
        for item in items:
            try:
                name, qty = item.split(':')
                cursor.execute('''
                    INSERT INTO orders (food_item, quantity, username)
                    VALUES (?, ?, ?)
                ''', (name, int(qty), username))
            except ValueError:
                continue

    return redirect(url_for('thankyou', ordered='yes'))


@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html',
                           user_logged_in=session.get('user_logged_in'),
                           username=session.get('username'))


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', debug=True, port=5090)




