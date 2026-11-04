from .roles import rol
def user_role(request):
    return {"user_role":rol(request.user)}
