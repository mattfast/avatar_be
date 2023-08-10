from users import get_user, create_user

def login(number):
    user = get_user(number)
    is_first = user is None

    if is_first:
        user = create_user(number)
        
    return user, is_first
