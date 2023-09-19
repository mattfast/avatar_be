from users import create_user, get_user

def login(token):
    user = get_user(token)
    is_first = user is None

    if is_first:
        print("CREATING USER")
        user = create_user(token)
    else:
        print("GOT EXISTING USER")

    return user, is_first
