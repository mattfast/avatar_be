from users import create_user, get_user


def login(number, is_sid=False):
    user = get_user(number, is_sid)
    is_first = user is None

    if is_first:
        user = create_user(number, is_sid)

    return user, is_first
