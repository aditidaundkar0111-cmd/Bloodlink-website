from flask import Flask
from config import config
from .models import User, db

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )
    app.config.from_object(config[config_name])
    db.init_app(app)
    from .routes import auth_bp, donor_bp, search_bp, admin_bp, main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(donor_bp, url_prefix='/api')
    app.register_blueprint(search_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    with app.app_context():
        db.create_all()

        admin_email = "admin@gmail.com"
        admin_password = "Admin@123"

        existing_admin = User.query.filter_by(email=admin_email).first()

        if not existing_admin:
            admin = User(
                name="Administrator",
                email=admin_email,
                phone="9999999999",
                role="admin",
                is_verified=True
            )
            admin.set_password(admin_password)

            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin created")

    return app
    
    
