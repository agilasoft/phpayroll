# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import sys

# Read version and dependencies from pyproject.toml
def get_pyproject_data():
	try:
		import tomllib
		with open('pyproject.toml', 'rb') as f:
			return tomllib.load(f)
	except ImportError:
		# Fallback for Python < 3.11
		try:
			import tomli as tomllib
			with open('pyproject.toml', 'rb') as f:
				return tomllib.load(f)
		except ImportError:
			pass
	except FileNotFoundError:
		pass
	return None

pyproject = get_pyproject_data()

if pyproject:
	project = pyproject.get('project', {})
	version = project.get('version', '0.0.1')
	install_requires = project.get('dependencies', [])
	authors = project.get('authors', [])
	author = authors[0].get('name', 'Agilasoft Technologies Inc.') if authors else 'Agilasoft Technologies Inc.'
	author_email = authors[0].get('email', 'info@agilasoft.com') if authors else 'info@agilasoft.com'
	description = project.get('description', 'Philippine Payroll')
else:
	# Fallback to requirements.txt and __init__.py if pyproject.toml doesn't exist
	with open('requirements.txt') as f:
		install_requires = [line.strip() for line in f if line.strip() and not line.startswith('#')]
	
	# Try to get version from __init__.py as last resort
	try:
		import importlib.util
		spec = importlib.util.spec_from_file_location("phpayroll", "phpayroll/__init__.py")
		phpayroll = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(phpayroll)
		version = phpayroll.__version__
	except Exception:
		version = '0.0.1'
	
	author = 'Agilasoft Technologies Inc.'
	author_email = 'info@agilasoft.com'
	description = 'Philippine Payroll'

setup(
	name='phpayroll',
	version=version,
	description=description,
	author=author,
	author_email=author_email,
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
