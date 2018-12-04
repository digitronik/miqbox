from setuptools import setup, find_packages


with open("README.md") as readme_file:
    readme = readme_file.read()

install_requirements = ["Click>=7.0", "libvirt-python>=4.8", "requests>=2.20", "bs4>=0.0.1"]

setup_requirements = ["setuptools_scm"]

setup(
    author="Nikhil Dhandre",
    author_email="ndhandre@redhat.com",
    classifiers=[
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Spin ManageIQ/CFME Appliance locally",
    entry_points={
        'console_scripts': [
            'miqbox=miqbox.miqbox:cli',
        ],
    },
    install_requires=install_requirements,
    long_description=readme,
    # include_package_data=True,
    setup_requires=setup_requirements,
    keywords='miqbox',
    name='miqbox',
    packages=find_packages(include=['miqbox']),
    url='https://github.com/digitronik/miqbox',
    version='0.1.0',
    license="GNU-2",
    zip_safe=False,
)
