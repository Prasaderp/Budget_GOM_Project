from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
import logging
from src import models

logger = logging.getLogger(__name__)

_CACHED_PASSWORD_HASHES: Dict[str, str] = {}

def _get_cached_password_hash(role: str) -> str:
    if role not in _CACHED_PASSWORD_HASHES:
        from src.routers.auth import hash_password
        password_map = {
            'officer1': 'officer1@123',
            'officer2': 'officer2@123',
            'assistant': 'assistant@123'
        }
        _CACHED_PASSWORD_HASHES[role] = hash_password(password_map[role])
    return _CACHED_PASSWORD_HASHES[role]


def create_taluka_user(
    db: Session,
    district: str,
    taluka_name: str,
    role: str,
    activated_by_username: str
) -> Optional[models.User]:
    dkey = district.lower().replace(' ', '_')
    if ' Taluka ' in taluka_name:
        taluka_part = taluka_name.split(' Taluka ')[-1]
    else:
        taluka_part = taluka_name
    
    taluka_name_mapping = {
        'बोरिवली': 'borivali', 'अंधेरी': 'andheri', 'कुर्ला': 'kurla',
        'भिवंडी': 'bhiwandi', 'मुरबाड': 'murbad', 'ठाणे': 'thane', 'कल्याण': 'kalyan',
        'अंबरनाथ': 'ambarnath', 'उल्हासनगर': 'ulhasnagar', 'शहापूर': 'shahapur', 'मिरा भाईंदर': 'mira_bhayandar',
        'अलिबाग': 'alibag', 'पेण': 'pen', 'पनवेल': 'panvel', 'उरण': 'uran', 'कर्जत': 'karjat',
        'खालापूर': 'khalapur', 'रोहा': 'roha', 'मुरुड': 'murud', 'सुधागड': 'sudhagad', 'महाड': 'mahad',
        'माणगाव': 'mangaon', 'तळा': 'tala', 'म्हसळा': 'mhasla', 'श्रीवर्धन': 'shrivardhan',
        'पोलादपूर': 'poladpur', 'अपर तहसिलदार पनवेल': 'upper_panvel',
        'पालघर': 'palghar', 'वसई': 'vasai', 'डहाणू': 'dahanu', 'तलासरी': 'talasari',
        'जव्हार': 'jawhar', 'वाडा': 'wada', 'मोखाडा': 'mokhada', 'विक्रमगड': 'vikramgad',
        'दापोली': 'dapoli', 'खेड': 'khed', 'गुहागर': 'guhagar', 'लांजा': 'lanja',
        'मंडणगड': 'mandangad', 'रत्नागिरी': 'ratnagiri', 'राजापूर': 'rajapur', 'चिपळूण': 'chiplun',
        'संगमेश्वर': 'sangameshwar', 'देवगड': 'devgad', 'कणकवली': 'kankavali', 'मालवण': 'malvan',
        'सावंतवाडी': 'sawantwadi', 'वेंगुर्ला': 'vengurla', 'वैभववाडी': 'vaibhavwadi', 'कुडाळ': 'kudal',
        'दोडामार्ग': 'dodamarg'
    }
    
    taluka_key = taluka_name_mapping.get(taluka_part, taluka_part.lower())
    tkey = f"{dkey}_{taluka_key}"
    
    role_map = {
        'officer1': 'o1',
        'officer2': 'o2', 
        'assistant': 'asst'
    }
    
    if role not in role_map:
        return None
    
    username = f"{tkey}_{role_map[role]}"
    full_name = f"{taluka_name} {role.replace('officer', 'Officer ').replace('assistant', 'Assistant')}"
    
    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        existing.is_active = True
        existing.activated_by = activated_by_username
        return existing
    
    new_user = models.User(
        username=username,
        password_hash=_get_cached_password_hash(role),
        full_name=full_name,
        level="taluka",
        unit=taluka_name,
        role=role,
        is_active=True,
        activated_by=activated_by_username,
        created_at=datetime.utcnow()
    )
    
    db.add(new_user)
    return new_user


def activate_taluka_users(
    db: Session,
    district: str,
    taluka_name: str,
    activated_by_username: str
) -> Dict[str, models.User]:
    users = {}
    roles = ['officer1', 'officer2', 'assistant']
    
    for role in roles:
        user = create_taluka_user(db, district, taluka_name, role, activated_by_username)
        if user:
            users[role] = user
    
    db.flush()
    
    taluka_mgmt = db.query(models.TalukaUserManagement).filter(
        models.TalukaUserManagement.district == district,
        models.TalukaUserManagement.taluka_name == taluka_name
    ).first()
    
    if not taluka_mgmt:
        taluka_mgmt = models.TalukaUserManagement(
            district=district,
            taluka_name=taluka_name,
            is_active=True,
            activated_at=datetime.utcnow(),
            activated_by_district_assistant=activated_by_username,
            last_modified=datetime.utcnow()
        )
        db.add(taluka_mgmt)
        db.flush()
    else:
        taluka_mgmt.is_active = True
        taluka_mgmt.activated_at = datetime.utcnow()
        taluka_mgmt.deactivated_at = None
        taluka_mgmt.activated_by_district_assistant = activated_by_username
        taluka_mgmt.last_modified = datetime.utcnow()
    
    if 'officer1' in users and users['officer1'].id:
        taluka_mgmt.officer1_user_id = users['officer1'].id
    if 'officer2' in users and users['officer2'].id:
        taluka_mgmt.officer2_user_id = users['officer2'].id
    if 'assistant' in users and users['assistant'].id:
        taluka_mgmt.assistant_user_id = users['assistant'].id
    
    try:
        from src.notification_service import send_taluka_activation_alert
        send_taluka_activation_alert(db, district, taluka_name, users)
    except Exception as e:
        logger.error(f"Failed to send taluka activation alert: {e}", exc_info=True)
    
    return users


def deactivate_taluka_users(
    db: Session,
    district: str,
    taluka_name: str,
    deactivated_by_username: str
) -> List[models.User]:
    deactivated_users = []
    
    users = db.query(models.User).filter(
        models.User.level == "taluka",
        models.User.unit == taluka_name,
        models.User.is_active == True
    ).all()
    
    for user in users:
        user.is_active = False
        deactivated_users.append(user)
    
    taluka_mgmt = db.query(models.TalukaUserManagement).filter(
        models.TalukaUserManagement.district == district,
        models.TalukaUserManagement.taluka_name == taluka_name
    ).first()
    
    if taluka_mgmt:
        taluka_mgmt.is_active = False
        taluka_mgmt.deactivated_at = datetime.utcnow()
        taluka_mgmt.last_modified = datetime.utcnow()
    
    try:
        from src.notification_service import send_taluka_deactivation_alert
        send_taluka_deactivation_alert(db, district, taluka_name, deactivated_users)
    except Exception as e:
        logger.error(f"Failed to send taluka deactivation alert: {e}", exc_info=True)
    
    return deactivated_users


def get_taluka_users_for_district(db: Session, district: str) -> Dict[str, Dict]:
    taluka_mgmts = db.query(models.TalukaUserManagement).filter(
        models.TalukaUserManagement.district == district,
        models.TalukaUserManagement.is_active == True
    ).all()
    
    result = {}
    
    for mgmt in taluka_mgmts:
        users = {}
        
        if mgmt.officer1_user_id:
            user = db.query(models.User).filter(
                models.User.id == mgmt.officer1_user_id,
                models.User.is_active == True
            ).first()
            if user:
                users['officer1'] = {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'is_active': user.is_active
                }
        
        if mgmt.officer2_user_id:
            user = db.query(models.User).filter(
                models.User.id == mgmt.officer2_user_id,
                models.User.is_active == True
            ).first()
            if user:
                users['officer2'] = {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'is_active': user.is_active
                }
        
        if mgmt.assistant_user_id:
            user = db.query(models.User).filter(
                models.User.id == mgmt.assistant_user_id,
                models.User.is_active == True
            ).first()
            if user:
                users['assistant'] = {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'is_active': user.is_active
                }
        
        if users:
            result[mgmt.taluka_name] = {
                'is_active': mgmt.is_active,
                'activated_at': mgmt.activated_at,
                'activated_by': mgmt.activated_by_district_assistant,
                'users': users
            }
    
    return result


def update_taluka_user_credentials(
    db: Session,
    user_id: int,
    new_username: Optional[str] = None,
    new_password: Optional[str] = None
) -> bool:
    user = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.level == "taluka"
    ).first()
    
    if not user:
        return False
    
    if new_username and new_username != user.username:
        existing_username = db.query(models.User).filter(
            models.User.username == new_username,
            models.User.id != user_id
        ).first()
        if existing_username:
            return False
        user.username = new_username
    
    if new_password:
        from src.routers.auth import hash_password
        user.password_hash = hash_password(new_password)
    
    return True


def sync_taluka_selection_with_management(
    db: Session,
    district: str,
    selected_talukas: List[str],
    district_assistant_username: str
):
    current_active_mgmts = db.query(models.TalukaUserManagement).filter(
        models.TalukaUserManagement.district == district,
        models.TalukaUserManagement.is_active == True
    ).all()
    
    current_active_taluka_names = {mgmt.taluka_name for mgmt in current_active_mgmts}
    selected_set = set(selected_talukas)
    
    to_activate = selected_set - current_active_taluka_names
    to_deactivate = current_active_taluka_names - selected_set
    
    for taluka_name in to_activate:
        activate_taluka_users(db, district, taluka_name, district_assistant_username)
    
    for taluka_name in to_deactivate:
        deactivate_taluka_users(db, district, taluka_name, district_assistant_username)
