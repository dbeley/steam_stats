import setuptools
import steam_stats

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="steam_stats",
    version=steam_stats.__version__,
    author="dbeley",
    author_email="dbeley@protonmail.com",
    description="Scrap steam games stats",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dbeley/steam_stats",
    packages=setuptools.find_packages(),
    include_package_data=True,
    entry_points={"console_scripts": ["steam_stats=steam_stats.__main__:main"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
    ],
    install_requires=[
        "requests",
        "pandas",
        "tqdm",
        "beautifulsoup4",
        "lxml",
        "urllib3",
        "openpyxl",
    ],
)
