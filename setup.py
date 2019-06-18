"""Setup file for the Holfuy retriever.
   Adapted from the Python Packaging Authority template."""

from setuptools import setup, find_packages  # Always prefer setuptools


DISTNAME = 'holfuyretriever'
LICENSE = 'GPLv3+'
AUTHOR = 'Johannes Landmann'
AUTHOR_EMAIL = 'j_landmann@gmx.de'
CLASSIFIERS = [
        # How mature is this project? Common values are
        # 3 - Alpha  4 - Beta  5 - Production/Stable
        'Development Status :: 2 - Pre-Alpha',
        # Indicate who your project is intended for
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License ' +
        'v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.7',
    ]

DESCRIPTION = 'Holfuy Camera Image Retriever'
LONG_DESCRIPTION = """
The Holfuy Camera Image Retriever is a small package to operationally retrieve 
and backup camera images from Holfuy cameras.
"""


req_packages = ['schedule']


setup(
    # Project info
    name=DISTNAME,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    # Version info
    use_scm_version=True,
    # Author details
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    # License
    license=LICENSE,
    classifiers=CLASSIFIERS,
    # What does your project relate to?
    keywords=['geosciences'],
    # We are a python 3 only shop
    python_requires='>=3.5',
    # Find packages automatically
    packages=find_packages(exclude=['docs']),
    # Include package data
    include_package_data=True,
    # Install dependencies
    install_requires=req_packages,
    # additional groups of dependencies here (e.g. development dependencies).
    extras_require={},
)
