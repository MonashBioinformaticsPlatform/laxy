"""Laxy clientside downloader

https://github.com/MonashBioinformaticsPlatform/laxy/laxy_downloader
"""

from setuptools import setup, find_packages
from codecs import open
from os import path
import laxy_downloader

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="laxy_downloader",
    version=laxy_downloader.__version__,
    description="Laxy clientside downloader",
    long_description=long_description,
    url="https://github.com/MonashBioinformaticsPlatform/laxy",
    author="Andrew Perry",
    author_email="Andrew.Perry@monash.edu",
    license="Apache",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 3 - Beta",
        # Indicate who your project is intended for
        "Intended Audience :: Science/Research",
        "Intended Audience :: System Administrators",
        "Topic :: Scientific/Engineering :: Bio-Informatics"
        # Pick your license as you wish (should match "license" above)
        "License :: OSI Approved :: Apache License",
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    keywords="Clientside download client for Laxy",
    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=["tests*"]),
    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        "asks==2.2.1",
        "requests==2.26.0",
        "toolz==0.10.0",
        "backoff==1.10.0",
        "attrdict==2.0.1",
        "trio==0.8.0",
        "psutil==5.8.0",
        "python-magic==0.4.15",
        "text-unidecode==1.3",
        "typing-extensions==3.10.0.0",
        "pyaria2 @ git+https://github.com/pansapiens/pyaria2.git#egg=pyaria2-0.2.1.2",
    ],
    # pip deprecated dependency_links :/
    # dependency_links=[
    #    "git+https://github.com/pansapiens/pyaria2.git#egg=pyaria2-0.2.1.2",
    #    # "https://github.com/pansapiens/pyaria2/tarball/master#egg=pyaria2-0.2.1.2"
    # ],
    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    # extras_require={
    #     'dev': ['prospector',
    #             'check-manifest'],
    #     'test': ['tox',
    #              'pytest'
    #              'coverage',
    #              'requests_mock'],
    # },
    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    # package_data={
    #      'sample': ['sample.dat'],
    # },
    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[('my_data', ['data/data_file'])],
    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        "console_scripts": [
            "laxydl=laxy_downloader.cli:main",
        ],
    },
    test_suite="tests",
)
