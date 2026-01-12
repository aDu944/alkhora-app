from setuptools import setup, find_packages

setup(
    name="management_dashboard",
    version="1.0.0",
    description="ALKHORA Company App - Custom ERPNext extensions and workspaces",
    author="ALKHORA",
    author_email="support@alkhora.com",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
)
