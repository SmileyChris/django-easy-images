#!/usr/bin/env python
import os
import sys
from cStringIO import StringIO

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
        cov = coverage()
        cov.start()
    failures = test_runner.run_tests(args)
    if not args:
        cov.stop()
        coverage_report(cov, report=not failures)
    sys.exit(failures)


def coverage_report(cov, report):
    """
    Outputs Coverage report to screen and coverage.xml.
    """
    include = ['easy_images*']
    omit = []
    # omit = ['easy_images/*/*']
    try:
        if report:
            log.info("\nCoverage Report (showing uncovered modules):")
            real_stdout = sys.stdout
            fake_stdout = StringIO()
            sys.stdout = fake_stdout
            try:
                cov.report(include=include, omit=omit)
            finally:
                sys.stdout = real_stdout
            fake_stdout.seek(0)
            for line in fake_stdout.readlines():
                line = line.rstrip()
                if line.endswith('100%'):
                    continue
                print(line)
        cov.html_report(include=include, omit=omit)
        # cov.xml_report(include=include, omit=omit)
    except misc.CoverageException as e:
        log.error("Coverage Exception: %s" % e)


if __name__ == '__main__':
    test_arg = sys.argv[1:] if len(sys.argv) > 1 else None
    runtests(test_arg)
