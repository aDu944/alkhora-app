from setuptools import setup, find_packages


setup(
    name="management_dashboard",
    version="1.0.0",
    description="ALKHORA Company App - Custom ERPNext extensions and workspaces",
    author="ALKHORA",
    author_email="support@alkhora.co",
    packages=find_packages(
        where=".",
        include=["management_dashboard", "management_dashboard.*"],
        exclude=["*.tests", "*.tests.*", "tests.*", "tests", "management_dashboard.page.*", "management_dashboard.doctype.*"]
    ),
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

