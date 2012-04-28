"""
Ubuntu tasks/utilities.
"""
import cuisine

def set_locale(locale='en_US'):
    """
    Set locale to avoid the warnings from perl and others about locale
    failures.
    """
    cuisine.sudo('locale-gen {locale}.UTF-8'.format(**vars()))
    cuisine.sudo('update-locale LANG={locale}.UTF-8 LC_ALL={locale}.UTF-8 LC_MESSAGES=POSIX'.format(**vars()))
