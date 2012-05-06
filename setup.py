from setuptools import setup, find_packages


setup(name = 'awsfabrictasks',
      description = 'Fabric tasks for Amazon Web Services with some extra utilities for Ubuntu.',
      version = '1.0.2',
      license = 'BSD',
      url = 'https://github.com/espenak/awsfabrictasks',
      author = 'Espen Angell Kristiansen',
      packages = find_packages(exclude=['ez_setup']),
      install_requires = ['distribute', 'boto>=2.0', 'Fabric>=1.4.1'],
      include_package_data = True,
      long_description = open('README.rst').read(),
      zip_safe = False,
      classifiers = [
          'Intended Audience :: Developers',
          'License :: OSI Approved',
          'Programming Language :: Python'
      ],
      entry_points = {
          'console_scripts': [
              'awsfab = awsfabrictasks.main:awsfab',
          ],
      }
)
