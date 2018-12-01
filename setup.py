from setuptools import setup, find_packages


with open("README.md") as readme_file:
    readme = readme_file.read()

install_requirements = ["Click>=7.0", "libvirt-python>=4.8", "requests>=2.20", "bs4>=0.0.1"]

setup_requirements = ["setuptools_scm"]

setup(
    name="miqbox",
    description="Spin ManageIQ/CFME Appliance locally",
    author="Nikhil Dhandre",
    author_email="ndhandre@redhat.com",
    keywords="miqbox",
    classifiers=[
        "Natural Language :: English",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=2.7",
    entry_points={"console_scripts": ["miqbox=miqbox.miqbox:cli"]},
    install_requires=install_requirements,
    long_description=readme,
    license="GNU-2",
    include_package_data=True,
    packages=find_packages(include=["miqbox"]),
    setup_requires=setup_requirements,
    url="https://github.com/digitronik/miqbox",
    version="0.1.0",
    zip_safe=False,
)
