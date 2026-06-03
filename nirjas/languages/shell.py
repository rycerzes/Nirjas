#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (C) 2020  Ayush Bhardwaj (classicayush@gmail.com),
Kaushlendra Pratap (kaushlendrapratap.9837@gmail.com)

SPDX-License-Identifier: LGPL-2.1

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
"""


from nirjas.languages.language_config import LanguageConfig


SHELL_CONFIG = LanguageConfig(
    display_language="Shell",
    parser_language="shell",
    comment_node_kinds=frozenset({"comment"}),
    single_line_prefixes=("#",),
)


def shellExtractor(file):
    return SHELL_CONFIG.extract(file)


def shellSource(file, new_file: str):
    """
    Extract source from Shell file and put at new_file.
    :param file: File to process
    :type file: string
    :param new_file: File to put source at
    :type new_file: string
    :return: Path to new file
    :rtype: string
    """
    with open(new_file, "w+") as f1:
        with open(file) as f:
            for line in f:
                content = line
                if "#" in line:
                    content = line[: line.find("#")].rstrip() + "\n"
                if content.strip() != "":
                    f1.write(content)
    f.close()
    f1.close()
    return new_file
