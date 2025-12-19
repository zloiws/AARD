import sys
from pathlib import Path
# Ensure backend package is importable when running this script directly
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal, Base, engine
from app.services.system_setting_service import SystemSettingService
from app.models.system_setting import SystemSetting

def main():
    # ensure tables exist
    Base.metadata.create_all(bind=engine)
    sess = SessionLocal()
    service = SystemSettingService(sess)
    try:
        service.set_setting('test.custom.setting', 42, category='system', description='test', updated_by='cli')
        val = service.get_setting('test.custom.setting')
        print('GOT:', val)
        row = sess.query(SystemSetting).filter(SystemSetting.key=='test.custom.setting').first()
        print('ROW:', row, getattr(row, 'value', None), getattr(row, 'value_type', None), getattr(row, 'is_active', None))
    finally:
        sess.close()

if __name__ == '__main__':
    main()


