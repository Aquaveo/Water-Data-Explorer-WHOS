from setuptools import setup, find_namespace_packages
from tethys_apps.app_installation import find_resource_files

# -- Apps Definition -- #
app_package = 'water_data_explorer_whos'
release_package = 'tethysapp-' + app_package

# -- Python Dependencies -- #
dependencies = []

# -- Get Resource File -- #
resource_files = find_resource_files('tethysapp/' + app_package + '/templates', 'tethysapp/' + app_package)
resource_files += find_resource_files('tethysapp/' + app_package + '/public', 'tethysapp/' + app_package)
resource_files += find_resource_files('tethysapp/' + app_package + '/workspaces', 'tethysapp/' + app_package)


setup(
    name=release_package,
    version='1.2.0',
    description='A tethys app that lets the user to visualize and query WSDL enpoints',
    long_description='',
    keywords='',
    author='Giovanni Romero Bustamante',
    author_email='gio.rombus@gmail.com',
    url='https://github.com/BYU-Hydroinformatics/Water-Data-Explorer-WHOS',
    license='BSD 3-Clause License',
    packages=find_namespace_packages(),
    package_data={'': resource_files},
    include_package_data=True,
    zip_safe=False,
    install_requires=dependencies,
)
