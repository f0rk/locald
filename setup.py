# Copyright 2020-2024, Ryan P. Kelly.

from setuptools import setup


setup(
    name="locald",
    version="1.5",
    description="run local services/microservices for development",
    author="Ryan P. Kelly",
    author_email="ryan@ryankelly.us",
    url="https://github.com/f0rk/locald",
    install_requires=[
        "daemonize",
        "psutil",
    ],
    tests_require=[
        "pytest",
    ],
    package_dir={"": "lib"},
    packages=["locald"],
    scripts=["tools/locald"],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development",
    ],
)
