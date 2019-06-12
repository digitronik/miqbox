from setuptools import setup, find_packages


with open("README.md") as readme_file:
    readme = readme_file.read()

install_requirements = [
    "bs4>=0.0.1",
    "Click>=5.0",
    "libvirt-python>=4.0",
    "paramiko~=2.3",
    "requests>=2.20",
    "ruamel.yaml~=0.15",
]

setup_requirements = ["setuptools_scm"]

setup(
    author="Nikhil Dhandre",
    author_email="nik.digitronik@live.com",
    classifiers=[
        "Natural Language :: English",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    python_requires=">=3.5",
    description="Spin ManageIQ/CFME Appliance locally.",
    entry_points={"console_scripts": ["miqbox=miqbox.miqbox:cli"]},
    install_requires=install_requirements,
    long_description=readme,
    long_description_content_type="text/markdown",
    include_package_data=True,
    setup_requires=setup_requirements,
    use_scm_version=True,
    keywords="miqbox",
    name="miqbox",
    packages=find_packages(include=["miqbox"]),
    url="https://github.com/digitronik/miqbox",
    license="GPLv2",
    zip_safe=False,
)
