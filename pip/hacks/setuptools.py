from __future__ import absolute_import

import os
import shutil
import tempfile
import sys

import pip


def mk_fetch_build_egg(location):
    def fetch_build_egg(dist, req):
        # Late import because reasons
        import pkg_resources

        # Modify sys.path so that the stuff we just installed can be found
        sys.path.insert(0, location)
        pkg_resources.working_set.add_entry(location)

        print(os.listdir(location))

        try:
            return pkg_resources.get_distribution(req)
        except pkg_resources.DistributionNotFound:
            tmpdir = tempfile.mkdtemp()
            try:
                pip.main(["install", "-t", location, "--build", tmpdir, str(req)])
                print(os.listdir(location))
                return pkg_resources.get_distribution(req)
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
    return fetch_build_egg


def mksetup(real_setup, location):
    def setup(**kwargs):
        # Late import because reasons
        from distutils.dist import Distribution

        distclass = kwargs.pop("distclass", Distribution)
        distclass.fetch_build_egg = mk_fetch_build_egg(location)

        kwargs["distclass"] = distclass

        return real_setup(**kwargs)
    return setup
