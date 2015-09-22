from __future__ import print_function
import sys
from os.path import expanduser, join, exists, dirname
from pprint import pprint
from fabric.api import task, env
from warnings import warn

from awsfabrictasks import default_settings

__all__ = ['Settings', 'print_settings', 'default_settings']



def import_module(name, package=None):
    __import__(name)
    return sys.modules[name]

class Settings(object):
    """
    Settings object inspired by django.conf.settings.
    """
    def __init__(self):
        self._apply_settings_from_module(default_settings)
        self._is_loaded = False

    def __getattribute__(self, attr):
        """
        Load settings automatically the first time an uppercase attribute
        (setting) is requested.
        """
        if attr.upper() == attr:
            if not self._is_loaded:
                if hasattr(env, 'awsfab_settings_module'):
                    self.load(env.awsfab_settings_module)
                else:
                    warn('Could not find the env.awsfab_settings_module. Make sure you run run awsfab tasks using the ``awsfab`` command (not fab)?')
        return super(Settings, self).__getattribute__(attr)

    def load(self, settings_module):
        if self._is_loaded:
            raise Exception('Can only load settings once.')
        custom_settings = import_module(settings_module)
        self._apply_settings_from_module(custom_settings)

        try:
            local_settings = import_module(settings_module + '_local')
        except ImportError:
            pass
        else:
            self._apply_settings_from_module(local_settings)
        self._is_loaded = True

    def set_settings(self, **settings):
        """
        Set all all the given settings as attributes of this object.

        :raise ValueError: If any of the keys in ``settings`` is not uppercase.
        """
        for key, value in settings.items():
            if not self._is_setting(key):
                raise ValueError('Settings must be all uppercase, and they can not begin with userscore (``_``).')
            setattr(self, key, value)

    def _is_setting(self, attrname):
        return attrname == attrname.upper() and not attrname.startswith('_')

    def _apply_settings_from_module(self, settings_module):
        for setting in dir(settings_module):
            if self._is_setting(setting):
                setattr(self, setting, getattr(settings_module, setting))

    def as_dict(self):
        """
        Get all settings (uppercase attributes on this object) as a dict.
        """
        dct = {}
        for attrname, value in self.__dict__.items():
            if attrname.upper() == attrname:
                dct[attrname] = value
        return dct

    def pprint(self):
        """
        Prettyprint the settings.
        """
        pprint(self.as_dict())

    def clear_settings(self):
        """
        Clear all settings (intended for testing). Deletes all uppercase attributes.
        """
        for setting in dir(self):
            if self._is_setting(setting):
                delattr(self, setting)

    def reset_settings(self, **settings):
        """
        Reset settings (intended for testing). Shortcut for::

            clear_settings()
            set_settings(**settings)
        """
        self.clear_settings()
        self.set_settings(**settings)

awsfab_settings = Settings()



@task
def print_settings():
    """
    Pretty-print the settings as they are seen by the system.
    """
    awsfab_settings.pprint()



@task
def print_default_settings():
    """
    Print ``default_settings.py``.
    """
    path = join(dirname(default_settings.__file__), 'default_settings.py')
    print(open(path).read())
