from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Manufacturer, Customer
from app.services.core import _ensure_canonical_actors


def test_canonical_actor_sync_preserves_identity_and_updates_source_fields():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        manufacturer = Manufacturer(name='Supplier A', country='Iran', city='Tehran', verification_status='Unverified', confidence=0.2)
        customer = Customer(name='Buyer A', country='Afghanistan', city='Herat', verification_status='Unverified', confidence=0.1)
        db.add_all([manufacturer, customer])
        db.commit()

        supplier1, buyer1 = _ensure_canonical_actors(db, manufacturer, customer)
        db.commit()

        manufacturer.phone = '09120000000'
        manufacturer.website = 'https://supplier.example'
        manufacturer.verification_status = 'Verified'
        manufacturer.confidence = 0.9
        customer.phone = '+93700000000'
        customer.verification_status = 'Verified'
        customer.confidence = 0.8
        supplier2, buyer2 = _ensure_canonical_actors(db, manufacturer, customer)

        assert supplier2.id == supplier1.id
        assert buyer2.id == buyer1.id
        assert supplier2.phone == manufacturer.phone
        assert supplier2.website == manufacturer.website
        assert supplier2.verification_status == 'Verified'
        assert supplier2.confidence == 0.9
        assert buyer2.phone == customer.phone
        assert buyer2.verification_status == 'Verified'
        assert buyer2.confidence == 0.8
    finally:
        db.close()
        Base.metadata.drop_all(engine)
