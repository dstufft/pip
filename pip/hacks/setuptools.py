import os
import sys
import tempfile
import shutil

from pip import parseopts
from pip.locations import distutils_scheme
from pip.commands.install import InstallCommand
from pip.log import logger
from pip.req import InstallRequirement, RequirementSet
from pkg_resources import working_set, parse_requirements


def mksetup_no_install(real_setup, tmpdir):
    """
    This exists because setuptools installs setup_requires, which bypasses the
    pip download routines. This means it has a seperate configuration for TLS,
    --pre, etc.

    So this metod hijacks that so it doesn't install anything. It is assumed
    that the requirements are already available in the system.
    """
    def setup(**kwargs):
        try:
            setup_requires = kwargs.pop("setup_requires")
        except KeyError:
            setup_requires = []

        if setup_requires:
            # Modify sys.path so that the stuff we just installed can be found
            sys.path.insert(0, distutils_scheme('', home=tmpdir)['purelib'])
            sys.path.insert(0, distutils_scheme('', home=tmpdir)['platlib'])

            working_set.add_entry(distutils_scheme('', home=tmpdir)['purelib'])
            working_set.add_entry(distutils_scheme('', home=tmpdir)['platlib'])

            for dist in working_set.resolve(
                    parse_requirements(setup_requires),
                    installer=None):
                working_set.add(dist)

        # Actually dispatch to the _real_ setup command
        return real_setup(**kwargs)
    return setup


def mksetup(real_setup, argv, tmpdir):
    """
    This exists because setuptools installs setup_requires, which bypasses
    the pip download routines. This means it has a seperate configuration for
    TLS, --pre, etc.

    So this method hijacks that so that pip now controls the setup_requires
    """
    def setup(**kwargs):
        try:
            setup_requires = kwargs.pop("setup_requires")
        except KeyError:
            setup_requires = []

        build_dir = None

        try:
            if setup_requires:
                # Get our Options
                _, args = parseopts(argv[1:])
                options, _ = InstallCommand().parse_args(args)

                # Taken from pip.basecommand:Command.main
                level = 1  # Notify
                level += options.verbose
                level -= options.quiet
                level = logger.level_for_integer(4 - level)
                complete_log = []
                logger.add_consumers(
                    (level, sys.stdout),
                    (logger.DEBUG, complete_log.append),
                )
                if options.log_explicit_levels:
                    logger.explicit_levels = True

                build_dir = tempfile.mkdtemp()

                # Taken from pip.commands.install:InstallCommand.run
                options.build_dir = os.path.abspath(build_dir)
                options.src_dir = os.path.abspath(options.src_dir)
                install_options = options.install_options or []

                options.ignore_installed = True
                install_options.append('--home=' + tmpdir)

                global_options = options.global_options or []

                index_urls = [options.index_url] + options.extra_index_urls

                if options.mirrors:
                    index_urls += options.mirrors

                session = InstallCommand()._build_session(options)
                finder = InstallCommand()._build_package_finder(
                    options,
                    index_urls,
                    session,
                )

                requirement_set = RequirementSet(
                    build_dir=options.build_dir,
                    src_dir=options.src_dir,
                    download_dir=options.download_dir,
                    download_cache=options.download_cache,
                    upgrade=options.upgrade,
                    as_egg=False,
                    ignore_installed=options.ignore_installed,
                    ignore_dependencies=options.ignore_dependencies,
                    force_reinstall=options.force_reinstall,
                    use_user_site=False,
                    target_dir=tmpdir,
                    session=session,
                    pycompile=options.compile,
                )

                for name in setup_requires:
                    requirement_set.add_requirement(
                        InstallRequirement.from_line(name, None),
                    )

                try:
                    requirement_set.prepare_files(
                        finder,
                        force_root_egg_info=False,
                        bundle=False,
                    )

                    requirement_set.install(install_options, global_options)

                    installed = ' '.join(
                        [
                            req.name
                            for req
                                in requirement_set.successfully_installed
                        ]
                    )
                    if installed:
                        logger.notify(
                            'Successfully installed %s' % installed
                        )
                finally:
                    # Clean up
                    if ((not options.no_clean)
                            and ((not options.no_install)
                                 or options.download_dir)):
                        requirement_set.cleanup_files(bundle=False)

            # Modify sys.path so that the stuff we just installed can
            # be found
            sys.path.insert(
                0,
                distutils_scheme('', home=tmpdir)['purelib'],
            )
            sys.path.insert(
                0,
                distutils_scheme('', home=tmpdir)['platlib'],
            )

            working_set.add_entry(distutils_scheme('', home=tmpdir)['purelib'])
            working_set.add_entry(distutils_scheme('', home=tmpdir)['platlib'])

            if setup_requires:
                for dist in working_set.resolve(
                        parse_requirements(setup_requires),
                        installer=None):
                    working_set.add(dist)

            # Actually dispatch to the _real_ setup command
            return real_setup(**kwargs)

        finally:
            if build_dir is not None:
                shutil.rmtree(build_dir, ignore_errors=True)
    return setup
