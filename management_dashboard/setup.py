from setuptools import setup


setup(
    name="management_dashboard",
    version="1.0.0",
    description="ALKHORA Company App - Custom ERPNext extensions and workspaces",
    author="ALKHORA",
    author_email="support@alkhora.co",
    packages=["management_dashboard", "management_dashboard.api", "management_dashboard.config"],
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

