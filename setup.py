# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import sys

# Try to read from pyproject.toml, fallback to requirements.txt for backward compatibility
try:
	import tomllib
	with open('pyproject.toml', 'rb') as f:
		pyproject = tomllib.load(f)
	install_requires = pyproject.get('project', {}).get('dependencies', [])
except (ImportError, FileNotFoundError):
	# Fallback for Python < 3.11 or if pyproject.toml doesn't exist
	try:
		import tomli as tomllib
		with open('pyproject.toml', 'rb') as f:
			pyproject = tomllib.load(f)
		install_requires = pyproject.get('project', {}).get('dependencies', [])
	except (ImportError, FileNotFoundError):
		# Final fallback to requirements.txt
		with open('requirements.txt') as f:
			install_requires = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# get version from __version__ variable in phpayroll/__init__.py
from phpayroll import __version__ as version

setup(
	name='phpayroll',
	version=version,
	description='Philippine Payroll',
	author='Agilasoft Technologies Inc.',
	author_email='info@agilasoft.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
