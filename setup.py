#!/usr/bin/env python
import sys
import os
from contextlib import contextmanager
from subprocess import check_call
import multiprocessing

from setuptools import setup, find_packages, Extension, Command
from distutils.command.build_ext import build_ext as distutils_build_ext

sources = map(lambda path: os.path.join('v8py', path),
              filter(lambda path: path.endswith('.cpp'),
                     os.listdir('v8py')))
libraries = ['v8_libplatform', 'v8_base', 'v8_nosnapshot',
             'v8_libbase', 'v8_libsampler',
             'icui18n', 'icuuc']
library_dirs = ['v8/out/native',
                'v8/out/native/obj.target/src',
                'v8/out/native/obj.target/third_party/icu']
if sys.platform.startswith('linux'):
    libraries.append('rt')
extension = Extension('v8py',
                      sources=sources,
                      include_dirs=['v8py', 'v8/include'],
                      library_dirs=library_dirs,
                      libraries=libraries,
                      extra_compile_args=['-std=c++11'],
                      )

@contextmanager
def cd(path):
    old_cwd = os.getcwd()
    try:
        yield os.chdir(path)
    finally:
        os.chdir(old_cwd)

DEPOT_TOOLS_PATH = os.path.join(os.getcwd(), 'depot_tools')
COMMAND_ENV = os.environ.copy()
COMMAND_ENV['PATH'] = DEPOT_TOOLS_PATH + os.path.pathsep + os.environ['PATH']
COMMAND_ENV.pop('CC', None)
COMMAND_ENV.pop('CXX', None)

def run(command):
    print command
    check_call(command, shell=True, env=COMMAND_ENV)

def v8_exists():
    def library_exists(library):
        if library == 'rt':
            return True
        lib_filename = 'lib{}.a'.format(library)
        for lib_dir in library_dirs:
            lib_path = os.path.join(lib_dir, lib_filename)
            print 'checking', lib_path
            if os.path.isfile(lib_path):
                print library, 'exists'
                return True
        print library, 'does not exist'
        return False
    return all(library_exists(lib) for lib in libraries)

def get_v8():
    if not os.path.isdir('depot_tools'):
        print 'installing depot tools'
        run('git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git')
    else:
        print 'updating depot tools'
        with cd('depot_tools'):
            run('git pull')

    if not os.path.isdir('v8/.git'):
        print 'downloading v8'
        run('fetch --force v8')
    else:
        print 'updating v8'
        with cd('v8'):
            run('gclient fetch')

    with cd('v8'):
        run('git checkout {}'.format('branch-heads/5.4'))
        run('gclient sync')

class BuildV8Command(Command):
    # currently no options
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass

    def run(self):
        if not v8_exists():
            get_v8()
            with cd('v8'):
                run('make native -j{} CFLAGS=-fPIC CXXFLAGS=-fPIC'.format(multiprocessing.cpu_count()))

class build_ext(distutils_build_ext):
    def build_extension(self, ext):
        self.run_command('build_v8')
        distutils_build_ext.build_extension(self, ext)

setup(
    name='v8py',
    version='0.5',

    author='Theodore Dubois',
    author_email='tblodt@icloud.com',
    url='https://github.com/tbodt/v8py',

    license='LGPLv3',

    packages=find_packages(),
    ext_modules=[extension],

    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    cmdclass={
        'build_ext': build_ext,
        'build_v8': BuildV8Command,
    }
)
