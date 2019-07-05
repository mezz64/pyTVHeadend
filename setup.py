# Copyright (c) 2017-2018 John Mihalic <https://github.com/mezz64>
# Licensed under the MIT license.

# Used this guide to create module
# http://peterdowns.com/posts/first-time-with-pypi.html

# git tag 0.1 -m "0.1 release"
# git push --tags origin master
#
# Upload to PyPI Live
# python setup.py register -r pypi
# python setup.py sdist upload -r pypi


from distutils.core import setup
setup(
    name='pyTVHeadend',
    packages=['pytvheadend'],
    version='0.0.2',
    description='Provides a python api to interact with a TVHeadend server.',
    author='John Mihalic',
    author_email='mezz64@users.noreply.github.com',
    url='https://github.com/mezz64/pyTVHeadend',
    download_url='https://github.com/mezz64/pytvheadend/tarball/0.0.2',
    keywords=['tv', 'tvheadend', 'api wrapper', 'homeassistant'],
    classifiers=[],
    )
