from getpass import getpass
from infrastructure.databases import get_database
from infrastructure.models.user_models import UserModel
from infrastructure.services.security_service import PasswordHasher

email = "admin@scentstation.local"

password = getpass("Nhap mat khau moi: ")
confirm = getpass("Nhap lai mat khau moi: ")

if password != confirm:
    raise SystemExit("Hai mat khau khong khop.")

if len(password) < 8:
    raise SystemExit("Mat khau phai co it nhat 8 ky tu.")

db = get_database()
session = db.session

try:
    user = session.query(UserModel).filter_by(email=email).first()

    if user is None:
        raise SystemExit(f"Khong tim thay tai khoan: {email}")

    user.password_hash = PasswordHasher().hash(password)
    user.failed_login_count = 0
    session.commit()

    print(f"Da cap nhat mat khau cho: {email}")
except Exception:
    session.rollback()
    raise
finally:
    db.remove_session()
    db.engine.dispose()
