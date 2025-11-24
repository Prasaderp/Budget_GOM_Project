from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
from src import models
from src.routers.auth import hash_password


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
    
    password_map = {
        'officer1': 'officer1@123',
        'officer2': 'officer2@123',
        'assistant': 'assistant@123'
    }
    
    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        existing.is_active = True
        existing.activated_by = activated_by_username
        return existing
    
    new_user = models.User(
        username=username,
        password_hash=hash_password(password_map[role]),
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
    
    return deactivated_users


def get_taluka_users_for_district(db: Session, district: str) -> Dict[str, Dict]:
    try:
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
            
            if not users and mgmt.is_active:
                auto_create_missing_users(db, district, mgmt.taluka_name, mgmt.activated_by_district_assistant or 'system')
                db.flush()
                
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
                
                if not users:
                    continue
                
            result[mgmt.taluka_name] = {
                'is_active': mgmt.is_active,
                'activated_at': mgmt.activated_at,
                'activated_by': mgmt.activated_by_district_assistant,
                'users': users
            }
        
        return result
    except Exception as e:
        print(f"Error getting taluka users for district {district}: {e}")
        return {}


def auto_create_missing_users(db: Session, district: str, taluka_name: str, activated_by: str):
    try:
        users = {}
        roles = ['officer1', 'officer2', 'assistant']
        
        for role in roles:
            user = create_taluka_user(db, district, taluka_name, role, activated_by)
            if user:
                users[role] = user
        
        db.flush()
        
        taluka_mgmt = db.query(models.TalukaUserManagement).filter(
            models.TalukaUserManagement.district == district,
            models.TalukaUserManagement.taluka_name == taluka_name
        ).first()
        
        if taluka_mgmt:
            if 'officer1' in users and users['officer1'].id:
                taluka_mgmt.officer1_user_id = users['officer1'].id
            if 'officer2' in users and users['officer2'].id:
                taluka_mgmt.officer2_user_id = users['officer2'].id
            if 'assistant' in users and users['assistant'].id:
                taluka_mgmt.assistant_user_id = users['assistant'].id
            
            taluka_mgmt.last_modified = datetime.utcnow()
    
    except Exception as e:
        print(f"Error auto-creating users for {taluka_name}: {e}")
        db.rollback()


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
        user.password_hash = hash_password(new_password)
    
    return True


def get_district_from_taluka_name(taluka_name: str) -> str:
    if ' Taluka ' in taluka_name:
        return taluka_name.split(' Taluka ')[0]
    return taluka_name


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


def cleanup_dummy_taluka_data(db: Session):
    dummy_pattern_users = db.query(models.User).filter(
        models.User.level == 'taluka',
        models.User.unit.like('% Taluka 1%') | 
        models.User.unit.like('% Taluka 2%') |
        models.User.unit.like('% Taluka 3%') |
        models.User.unit.like('% Taluka 4%') |
        models.User.unit.like('% Taluka 5%') |
        models.User.unit.like('% Taluka 6%') |
        models.User.unit.like('% Taluka 7%') |
        models.User.unit.like('% Taluka 8%') |
        models.User.unit.like('% Taluka 9%') |
        models.User.unit.like('% Taluka 10%') |
        models.User.unit.like('% Taluka 11%') |
        models.User.unit.like('% Taluka 12%') |
        models.User.unit.like('% Taluka 13%') |
        models.User.unit.like('% Taluka 14%') |
        models.User.unit.like('% Taluka 15%') |
        models.User.unit.like('% Taluka 16%') |
        models.User.unit.like('% Taluka 17%') |
        models.User.unit.like('% Taluka 18%') |
        models.User.unit.like('% Taluka 19%') |
        models.User.unit.like('% Taluka 20%')
    ).all()
    
    for user in dummy_pattern_users:
        db.delete(user)
    
    dummy_pattern_mgmt = db.query(models.TalukaUserManagement).filter(
        models.TalukaUserManagement.taluka_name.like('% Taluka 1%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 2%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 3%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 4%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 5%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 6%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 7%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 8%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 9%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 10%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 11%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 12%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 13%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 14%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 15%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 16%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 17%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 18%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 19%') |
        models.TalukaUserManagement.taluka_name.like('% Taluka 20%')
    ).all()
    
    for mgmt in dummy_pattern_mgmt:
        db.delete(mgmt)
    
    dummy_selections = db.query(models.DistrictTalukaSelection).all()
    for selection in dummy_selections:
        if selection.selected_talukas:
            cleaned_talukas = [t for t in selection.selected_talukas 
                             if not any(f'Taluka {i}' in t for i in range(1, 21))]
            if len(cleaned_talukas) != len(selection.selected_talukas):
                selection.selected_talukas = cleaned_talukas
    
    db.commit()
