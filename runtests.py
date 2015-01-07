#!/usr/bin/env python
import os
import sys
try:
    from io import BytesIO
except ImportError:
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO

from coverage import coverage, misc
from distutils import log

import django
from django.conf import settings
from django.test.utils import get_runner


def runtests(args=None):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'easy_images.tests.settings'
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=True)
    if not args:
        import setuptools
        packages = [p for p in setuptools.find_packages() if p.find('.') == -1]
        cov = coverage(source=packages)
        cov.start()
    failures = test_runner.run_tests(args)
    if not args:
        cov.stop()
        coverage_report(cov, report=True)  # not failures)
    sys.exit(failures)


def coverage_report(cov, report):
    """
    Outputs Coverage report to screen and html.
    """
    try:
        if report:
            log.info("\nCoverage Report (showing uncovered modules):")
            real_stdout = sys.stdout
            fake_stdout = BytesIO()
            sys.stdout = fake_stdout
            try:
                cov.report()
            finally:
                sys.stdout = real_stdout
            fake_stdout.seek(0)
            for line in fake_stdout.readlines():
                line = line.rstrip()
                if line.endswith('100%'):
                    continue
                print(line)
        cov.html_report()
        # cov.xml_report()
    except misc.CoverageException as e:
        log.error("Coverage Exception: %s" % e)


if __name__ == '__main__':
    test_arg = sys.argv[1:] if len(sys.argv) > 1 else None
    runtests(test_arg)
