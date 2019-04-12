#!/usr/bin/env python3
from setuptools import setup

setup(
      name="py-winusb"
    , version="0.2.0.1"
    , packages=["pywinusb"]
    , url="https://github.com/Mati365/pyWinUSB"
    , license="MIT"
    , author="Mateusz Bagiński"
    , author_email="cziken58@gmail.com"
    , description="Tool that helps with creating bootable Windows USB drives"
    , long_description=open("README.rst").read()
    , zip_safe=False
    , entry_points={
        "console_scripts": ["pywinusb=pywinusb.__main__:main"]
    }
    , platforms="linux"
    , keywords=["windows", "usb", "installer"]
    , package_data={"pywinusb": ["requirements.txt"]}
    , include_package_data=True
    , classifiers=[
          "Development Status :: 2 - Pre-Alpha"
        , "Intended Audience :: Developers"
        , "Intended Audience :: Information Technology"
        , "Programming Language :: Python"
        , "Programming Language :: Python :: 3"
        , "Programming Language :: Python :: 3.3"
        , "Programming Language :: Python :: 3.4"
    ]
)
