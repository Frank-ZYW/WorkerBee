# -*- coding: utf-8 -*-

import sys
import argparse

from workerbee.__version__ import VERSION
from workerbee.cmd.commands import startproject, genspider

optional_title = 'Optional arguments'


class CapitalisedHelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog):
        super(CapitalisedHelpFormatter, self).__init__(prog, indent_increment=2, max_help_position=30, width=200)
        self._action_max_length = 20

    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = 'Usage: '
        return super(CapitalisedHelpFormatter, self).add_usage(
            usage, actions, groups, prefix)

    class _Section(object):

        def __init__(self, formatter, parent, heading=None):
            self.formatter = formatter
            self.parent = parent
            self.heading = heading
            self.items = []

        def format_help(self):
            # format the indented section
            if self.parent is not None:
                self.formatter._indent()
            join = self.formatter._join_parts
            item_help = join([func(*args) for func, args in self.items])
            if self.parent is not None:
                self.formatter._dedent()

            # return nothing if the section was empty
            if not item_help:
                return ''

            # add the heading if the section was non-empty
            if self.heading is not argparse.SUPPRESS and self.heading is not None:
                current_indent = self.formatter._current_indent
                if self.heading == optional_title:
                    heading = '%*s%s:\n' % (current_indent, '', self.heading)
                else:
                    heading = '%*s%s:' % (current_indent, '', self.heading)
            else:
                heading = ''

            return join(['\n', heading, item_help])


parser = argparse.ArgumentParser(
    description='WorkerBee %s - Data filter components Based on Scrapy, Scrapy-Redis' % VERSION,
    formatter_class=CapitalisedHelpFormatter,
    add_help=False
)
parser._optionals.title = optional_title

parser.add_argument('-v', '--version', action='version', version=VERSION, help='Get version of WorkerBee')
parser.add_argument('-h', '--help', action='help', help='Show this help message and exit')

subparsers = parser.add_subparsers(dest='command', title='Available commands', metavar='')

parser_init = subparsers.add_parser('startproject', help='Create new WorkerBee style project')
parser_init.add_argument('projectname', default='WorkerBeeTemplate', nargs='?', type=str, help='project name')

parser_init = subparsers.add_parser('genspider', help='Generate new spider using pre-defined templates')
parser_init.add_argument('spidername', default='default', nargs='?', type=str, help='spider name')

# show help info when no args
if len(sys.argv[1:]) == 0:
    parser.print_help()
    parser.exit()


def cmd():
    """
    run from cmd
    :return:
    """
    args = parser.parse_args()
    command = args.command
    if command == 'startproject':
        startproject(args.projectname)
    elif command == 'genspider':
        genspider(args.spidername)
    else:
        parser.print_help()
        parser.exit()


if __name__ == '__main__':
    cmd()
