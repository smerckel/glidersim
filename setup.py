#!/usr/bin/env python

import os
from setuptools import find_packages, setup, Extension


about = {'name':"glidersim"}


with open(f"{about['name']}/_version.py", encoding="utf-8") as f:
    exec(f.read(), about)

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md'), encoding='utf8') as fh:
    long_description = fh.read()

with open('requirements.txt') as fobj:
    install_requires = [line.strip() for line in fobj]



setup(
    name=about['name'],
    version=about['__version__'],
    description='Ocean glider simulator',
    long_description=long_description,
    url='https://github.com/',
    author='Lucas Merckelbach',
    author_email='lucas.merckelbach@hereon.de',
    license='GPLv3',
    #packages=find_packages(where='.', exclude=['tests', 'docs', 'examples']),
    packages = ['glidersim'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GPLv3 License',
        'Environment :: Console',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.9',
    ],
    keywords=['ocean gliders', 'glider flight', 'oceanography'],
    install_requires=install_requires,
)
