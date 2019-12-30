import setuptools


with open ('README.md', 'r') as fh:
	long_description = fh.read()

setuptools.setup(
	name = 'pyanova-api',
	author = 'Ammar Zuberi',
	author_email = 'az@0f.tf',
	description = 'A Python 3 library for programmatically accessing Anova WiFi-enabled sous vide cookers through the Anova API.',
	long_description = long_description,
	long_description_content_type = 'text/markdown',
	url = 'https://github.com/ammarzuberi/pyanova-api',
	version = '0.0.1',
	python_requires='>=3.6',
	packages = ['anova'],
	install_requires = ['requests']
)