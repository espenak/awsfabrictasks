from setuptools import setup, find_packages
from awsfabrictasks import version


setup(name = 'awsfabrictasks',
      description = 'Fabric tasks for Amazon Web Services.',
      version = version,
      license = 'BSD',
      url = 'https://github.com/espenak/awsfabrictasks',
      author = 'Espen Angell Kristiansen',
      packages = find_packages(exclude=['ez_setup']),
      install_requires = ['boto>=2.4.1', 'Fabric>=1.4.1'],
      include_package_data = True,
      long_description = 'See https://github.com/espenak/awsfabrictasks',
      zip_safe = True,
      classifiers = [
          'Intended Audience :: Developers',
          'License :: OSI Approved',
          'Programming Language :: Python'
      ],
      entry_points = {
          'console_scripts': [
              'awsfab = awsfabrictasks.main:awsfab',
          ],
      },
      test_suite = 'nose.collector'
)
