"""
SPDX-License-Identifier: Apache-2.0
Copyright (c) 2024, Ampere Computing LLC
"""

import os
import re
from ..constants.arch_strings import AARCH64_ARCHS, NON_AARCH64_ARCHS
from ..constants.arch_specific_libs import ARCH_SPECIFIC_LIBS
from ..constants.arch_specific_options import X86_SPECIFIC_OPTS
from ..constants.arch_specific_options import NEOVERSE_SPECIFIC_OPTS
from ..constants.arch_specific_options import AMPEREONE_SPECIFIC_OPTS
from ..parsers.continuation_parser import ContinuationParser
from ..reports.issues.arch_specific_library_issue import ArchSpecificLibraryIssue
from ..reports.issues.arch_specific_build_option_issue import ArchSpecificBuildOptionIssue
from ..reports.issues.arch_specific_build_option_issue import NeoverseSpecificBuildOptionIssue
from ..reports.issues.arch_specific_build_option_issue import AmpereoneSpecificBuildOptionIssue
from ..reports.issues.define_other_arch_issue import DefineOtherArchIssue
from .scanner import Scanner


class CMakeScanner(Scanner):
    """Scanner that scans CMake"""

    CMAKE_NAMES = ['CMakeLists.txt']

    X86_SPECIFIC_OPTS_RE_PROG = re.compile(r'-m(%s)' %
                                            '|'.join([(r'%s\b' % x) for x in X86_SPECIFIC_OPTS]))
    ARCH_SPECIFIC_LIBS_RE_PROG = re.compile(r'(?:find_package|find_library)\((%s)' %
                                            '|'.join([(r'%s\b' % x) for x in ARCH_SPECIFIC_LIBS]))
    NEOVERSE_SPECIFIC_OPTS_RE_PROG = re.compile(r'-m(cpu|tune)=(%s)' %
                                            '|'.join([(r'%s\b' % x) for x in NEOVERSE_SPECIFIC_OPTS]))
    AMPEREONE_SPECIFIC_OPTS_RE_PROG = re.compile(r'-m(cpu|tune)=(%s)' %
                                            '|'.join([(r'%s\b' % x) for x in AMPEREONE_SPECIFIC_OPTS]))
    OTHER_ARCH_CPU_LINE_RE_PROG = re.compile(r'(?:CMAKE_SYSTEM_PROCESSOR).*(%s)' %
                                  '|'.join(NON_AARCH64_ARCHS))
    AARCH64_CPU_LINE_RE_PROG = re.compile(r'(?:CMAKE_SYSTEM_PROCESSOR).*(%s)' %
                                  '|'.join(AARCH64_ARCHS))

    def accepts_file(self, filename):
        basename = os.path.basename(filename)
        return basename in CMakeScanner.CMAKE_NAMES

    def scan_file_object(self, filename, file, report):
        continuation_parser = ContinuationParser()
        other_arch_cpu_condition = None
        seen_aarch64_cpu_condition = False
        seen_neoverse_build_flag = False
        seen_ampere1_build_flag = False

        for lineno, line in enumerate(file, 1):
            line = continuation_parser.parse_line(line)

            if not line:
                continue

            match = CMakeScanner.ARCH_SPECIFIC_LIBS_RE_PROG.search(line)
            if match:
                lib_name = match.group(1)
                report.add_issue(ArchSpecificLibraryIssue(
                    filename, lineno + 1, lib_name))
            match = CMakeScanner.X86_SPECIFIC_OPTS_RE_PROG.search(line)
            if match:
                opt_name = match.group(1)
                report.add_issue(ArchSpecificBuildOptionIssue(
                    filename, lineno + 1, opt_name))
            match = CMakeScanner.NEOVERSE_SPECIFIC_OPTS_RE_PROG.search(line)
            if match:
                seen_aarch64_cpu_condition = True
                seen_neoverse_build_flag = True
                opt_name = match.group(1)
                opt_value = match.group(2)
                report.add_issue(NeoverseSpecificBuildOptionIssue(
                    filename, lineno + 1, opt_name, opt_value))
            match = CMakeScanner.AMPEREONE_SPECIFIC_OPTS_RE_PROG.search(line)
            if match:
                seen_aarch64_cpu_condition = True
                seen_ampere1_build_flag = True
            match = CMakeScanner.OTHER_ARCH_CPU_LINE_RE_PROG.search(line)
            if match:
                other_arch_cpu_condition = line
            match = CMakeScanner.AARCH64_CPU_LINE_RE_PROG.search(line)
            if match:
                seen_aarch64_cpu_condition = True
        if other_arch_cpu_condition and not seen_aarch64_cpu_condition:
            report.add_issue(DefineOtherArchIssue(filename, lineno + 1, other_arch_cpu_condition))
        if seen_neoverse_build_flag and not seen_ampere1_build_flag:
            report.add_issue(AmpereoneSpecificBuildOptionIssue(filename, lineno + 1))
