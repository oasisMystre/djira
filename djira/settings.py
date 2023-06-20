from django.conf import settings
from django.test.signals import setting_changed


from rest_framework.settings import perform_import

DEFAULT_JIRA_SETTINGS = {
    "MIDDLEWARE_CLASSES": [],
    "SOCKET_INSTANCE": "djira.socket.sio",
    "AUTHENTICATION_CLASSES": [],
    "PERMISSION_CLASSES": ["djira.permissions.AllowAny"],
    "DEFAULT_PAGINATION_CLASS": "djira.pagination.PagePagination",
    "PAGE_SIZE": 16,
}

IMPORT_STRINGS = [
    "SOCKET_INSTANCE",
    "PERMISSION_CLASSES",
    "MIDDLEWARE_CLASSES",
    "AUTHENTICATION_CLASSES",
    "DEFAULT_PAGINATION_CLASS",
]


def shallow_merge(default: dict, new: dict):
    """
    Shallow merge two objects by combining their contents.
    If a  value is str or int, it is replaced with the new object.
    """
    result = dict()

    for key, value in dict.items(default):
        if key in new:
            if isinstance(value, (list, tuple)):
                result[key] = value + new[key]
            elif isinstance(value, dict):
                result[key].update(new[key])
            else:
                result[key] = new[key]
        else:
            result[key] = default[key]

    return result


class JiraSettings:
    def __init__(self):
        self._user_settings = shallow_merge(
            DEFAULT_JIRA_SETTINGS,
            getattr(settings, "DJIRA_SETTINGS", {}),
        )
        self._cached_attrs = set()

    @property
    def user_settings(self):
        return self._user_settings

    def __getattr__(self, __name: str):
        value = self.user_settings[__name]

        if __name in IMPORT_STRINGS:
            return perform_import(value, __name)

        self._cached_attrs.add(__name)
        setattr(self, __name, value)

        return value

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)

        self._cached_attrs.clear()

        if hasattr(self, "_user_settings"):
            delattr(self, "_user_settings")


jira_settings = JiraSettings()


def reload_api_settings(*args, **kwargs):
    setting = kwargs["setting"]
    if setting == "DJIRA_SETTINGS":
        jira_settings.reload()


setting_changed.connect(reload_api_settings)
