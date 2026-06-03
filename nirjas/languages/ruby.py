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


RUBY_CONFIG = LanguageConfig(
    display_language="Ruby",
    parser_language="ruby",
    comment_node_kinds=frozenset({"comment"}),
    single_line_prefixes=("#",),
    multi_line_delimiters=(("=begin", "=end"),),
)


def rubyExtractor(file):
    return RUBY_CONFIG.extract(file)


def rubySource(file, new_file: str):
    """
    Extract source from Ruby file and put at new_file.
    :param file: File to process
    :type file: string
    :param new_file: File to put source at
    :type new_file: string
    :return: Path to new file
    :rtype: string
    """
    copy = True
    with open(new_file, "w+") as f1:
        with open(file) as f:
            for line in f:
                content = ""
                found = False
                if "=begin" in line:
                    pos = line.find("=begin")
                    content = line[:pos].rstrip()
                    line = line[pos:]
                    copy = False
                    found = True
                if "=end" in line:
                    content = content + line[line.rfind("=end") + 4:]
                    line = content
                    copy = True
                    found = True
                if "#" in line:
                    content = line[: line.find("#")].rstrip() + "\n"
                    found = True
                if not found:
                    content = line
                if copy and content.strip() != "":
                    f1.write(content)
    f.close()
    f1.close()
    return new_file
