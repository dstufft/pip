import codecs
import os
import re
import stat
import sys
import zipfile

from distutils import log
from distutils.core import Command

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


here = os.path.abspath(os.path.dirname(__file__))

MAIN_PY = b"""
#!python
import sys

from pip.__main__ import main


if __name__ == "__main__":
    sys.exit(main())
""".lstrip()


class BuildExecutable(Command):

    user_options = [
        ("build-executable=", None, "The build directory for the executable."),
    ]

    def initialize_options(self):
        self.build_executable = None

    def finalize_options(self):
        build_ci = self.get_finalized_command("build")
        build_base = build_ci.build_base

        if self.build_executable is None:
            self.build_executable = os.path.join(build_base, "exe")

    def run(self):
        self.run_command("build")

        build_ci = self.get_finalized_command("build")
        lib_dir = build_ci.build_lib

        log.info("creating the executable.")

        try:
            os.makedirs(self.build_executable)
        except IOError:
            pass

        exe = os.path.join(self.build_executable, "pip.exe")

        with zipfile.PyZipFile(exe, "w", optimize=0) as pyz:
            # Add the items that we included as part of our source code into
            # the zip file.
            for dirname in sorted(os.listdir(lib_dir)):
                pyz.writepy(os.path.join(lib_dir, dirname))

            # Add the __main__.py
            pyz.writestr("__main__.py", MAIN_PY)

        # Mark our file as executable
        mode = os.stat(exe).st_mode
        os.chmod(exe, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class PyTest(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)

        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest

        sys.exit(pytest.main(self.test_args))


def read(*parts):
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    return codecs.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

long_description = read('README.rst')

tests_require = ['pytest', 'virtualenv>=1.10', 'scripttest>=1.3', 'mock']


setup(
    name="pip",
    version=find_version("pip", "__init__.py"),
    description="The PyPA recommended tool for installing Python packages.",
    long_description=long_description,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: PyPy"
    ],
    keywords='easy_install distutils setuptools egg virtualenv',
    author='The pip developers',
    author_email='python-virtualenv@groups.google.com',
    url='https://pip.pypa.io/',
    license='MIT',
    packages=find_packages(exclude=["contrib", "docs", "tests*", "tasks"]),
    package_data={
        "pip._vendor.certifi": ["*.pem"],
        "pip._vendor.requests": ["*.pem"],
        "pip._vendor.distlib._backport": ["sysconfig.cfg"],
        "pip._vendor.distlib": ["t32.exe", "t64.exe", "w32.exe", "w64.exe"],
    },
    entry_points={
        "console_scripts": [
            "pip=pip:main",
            "pip%s=pip:main" % sys.version[:1],
            "pip%s=pip:main" % sys.version[:3],
        ],
    },
    tests_require=tests_require,
    zip_safe=False,
    extras_require={
        'testing': tests_require,
    },
    cmdclass={
        'build_executable': BuildExecutable,
        'test': PyTest,
    },
)
