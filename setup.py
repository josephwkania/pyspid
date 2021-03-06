import glob

from setuptools import find_packages, setup

version = "0.0.1"

with open("requirements.txt") as f:
    required = f.read().splitlines()

setup(
    name="spidpy",
    version=version,
    packages=find_packages(),
    author="Joseph W Kania",
    scripts=glob.glob("bin/*"),
    install_requirements=required,
)
