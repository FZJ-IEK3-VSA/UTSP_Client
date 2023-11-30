import os
import setuptools  # type: ignore

dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, "requirements.txt")) as f:
    required_packages = f.read().splitlines()
with open(os.path.join(dir_path, "README.md"), "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="utspclient",
    version="0.1.6",
    author="David Neuroth",
    author_email="d.neuroth@fz-juelich.de",
    description="Universal Time Series Provider Client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/FZJ-IEK3-VSA/UTSP_Client",
    include_package_data=True,
    packages=setuptools.find_packages(),
    package_data={"utspclient": ["py.typed"]},
    install_requires=required_packages,
    setup_requires=["setuptools-git"],
    license="MIT license",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords=["time series", "load profile", "thermal load", "electricity load"],
)
