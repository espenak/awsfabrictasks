"""
Ubuntu utilities.
"""
from fabric.api import sudo

def set_locale(locale='en_US'):
    """
    Set locale to avoid the warnings from perl and others about locale
    failures.
    """
    sudo('locale-gen {locale}.UTF-8'.format(**vars()))
    sudo('update-locale LANG={locale}.UTF-8 LC_ALL={locale}.UTF-8 LC_MESSAGES=POSIX'.format(**vars()))
