from setuptools import setup
import fastentrypoints

setup(
    name='pica-parse',
    version='0.0',
    author='FID-Judaica, Goethe Universität',
    license='MLP 2.0/EUPL 1.1',
    author_email='a.christianson@ub.uni-frankfurt.de',
    url='https://github.com/FID-Judaica/pica-parse.py',
    description='Tools for parsing and iterating '
                'on plain-text Pica+ record dumps.',
    long_description=open('README.rst').read(),
    py_modules=['pica_parse'],
    # entry_points={'console_scripts': ['pica-parse=pica_parse:main']},
)
