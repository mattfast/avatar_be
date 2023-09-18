from users import create_user, get_user

def login(number, is_cookie=False):
    user = get_user(number, is_cookie=is_cookie)
    is_first = user is None

    if is_first:
        print("CREATING USER")
        user = create_user(number, is_cookie=is_cookie)
    else:
        print("GOT EXISTING USER")

    return user, is_first
