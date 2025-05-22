from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user, login_user, logout_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('home.html')

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Aquí procesar el formulario de contacto
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        # Puedes agregar lógica para enviar correo o guardar el mensaje
        flash('Thank you for contacting us! We will get back to you soon.', 'success')
        return redirect(url_for('main.contact'))
    return render_template('contact.html')

@main_bp.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        # Aquí deberías autenticar al usuario
        email = request.form.get('email')
        password = request.form.get('password')
        # Importa dentro de la función para evitar import circular
        from src.models.user import User, db
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Signed in successfully.', 'success')
            return redirect(url_for('main.home'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('signin.html')

@main_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        from src.models.user import User, db
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
            return redirect(url_for('main.signup'))
        user = User(fullname=fullname, email=email, user_type='customer')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully. Please sign in.', 'success')
        return redirect(url_for('main.signin'))
    return render_template('signup.html')

@main_bp.route('/signout')
@login_required
def signout():
    logout_user()
    flash('Signed out successfully.', 'info')
    return redirect(url_for('main.home'))

@main_bp.route('/user_home')
@login_required
def user_home():
    return render_template('user_home.html')

@main_bp.route('/qa')
def qa():
    return render_template('qa.html')

# Puedes agregar más rutas principales aquí según tus necesidades
