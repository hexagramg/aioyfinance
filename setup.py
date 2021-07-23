from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / 'README.md').read_text(encoding='utf-8')


setup(
    name='aioyfinance',  # Required

    version='0.1',  # Required

    description='Yahoo Finance asynchronous data downloader',  # Optional

    long_description=long_description,  # Optional

    long_description_content_type='text/markdown',  # Optional (see note above)

    url='https://github.com/hexagramg/aioyfinance',  # Optional

    author='hexagramg',  # Optional

    classifiers=[  # Optional
        "Development Status :: 2 - Pre-Alpha"
        'Intended Audience :: Developers',

        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)'
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
    ],

    keywords='setuptools, development',  # Optional

    package_dir={'': 'src'},  # Optional

    packages=find_packages(where='src'),  # Required

    python_requires='>=3.9, <4',

    install_requires=['aiohttp', 'beautifulsoup4'],  # Optional

    extras_require={  # Optional
        'dev': ['pandas'],
        'test': ['pandas', 'pytest'],
    },

    project_urls={  # Optional
        'Source': 'https://github.com/hexagramg/aioyfinance',
    },
)
