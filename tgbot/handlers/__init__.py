from .user import user_router
from .admin import admin_router
from .project import project_router
from .social import social_router
from .back import back_router

routers_list = [
    user_router,
    admin_router,
    project_router,
    social_router,
    back_router,
]

__all__ = [
    "routers_list",
]
