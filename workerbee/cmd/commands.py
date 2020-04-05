# -*- coding: utf-8 -*-

from os.path import join, exists, abspath
from os import getcwd, makedirs
from jinja2 import Environment, PackageLoader, select_autoescape
from scrapy.utils.project import get_project_settings

# Define template environment(place to hold templates)
ENV = Environment(loader=PackageLoader('workerbee'), autoescape=select_autoescape(['j2']))


def startproject(projectname):
    projectname_c = projectname.capitalize()
    execute_path = abspath(getcwd())
    dirs = join(execute_path, projectname, projectname, 'spiders')
    exists(dirs) or makedirs(dirs)

    workplace = join(execute_path, projectname)
    _make_file(join(workplace, 'scrapy.cfg'), _get_content(ENV, 'scrapy.j2', projectName=projectname))
    _make_file(join(workplace, '__version__.py'), _get_content(ENV, 'version.j2'))

    files = ['middlewares', 'settings']
    in_workplace = join(workplace, projectname)
    for each in files:
        file_path = join(in_workplace, each + '.py')
        content = _get_content(ENV, each + '.j2', projectName=projectname, projectNameC=projectname_c)
        _make_file(file_path, content)
    _make_file(join(in_workplace, '__init__.py'), '')
    _make_file(join(in_workplace, 'spiders', '__init__.py'), '')

    print("New WorkerBee project '%s', using template, created in:\n%s" % (projectname, workplace))
    print("\nYou can start your first spider with:\ncd %s\nworkerbee genspider example" % projectname)


def genspider(spidername):
    execute_path = abspath(getcwd())
    if not exists(join(execute_path, 'scrapy.cfg')):
        print("\033[1;31mPlease execute the command in the path where exist scrapy.cfg\033[0m")
        return

    spidername_c = spidername.capitalize()
    projectname = get_project_settings()['BOT_NAME']
    file_path = join(execute_path, projectname, 'spiders', spidername + '.py')
    content = _get_content(ENV, 'spider.j2', spiderName=spidername, spiderNameC=spidername_c)
    _make_file(file_path, content)
    print("Created spider '%s' using template in module:\n    %s.spiders.%s" % (spidername, projectname, spidername))


def _make_file(file_path, content):
    """
    :param file_path: file path(include file name)
    :param content: file content
    :return None
    """
    with open(file_path, 'w') as f:
        f.write(content)


def _get_content(env, template_name, *args, **kwargs):
    """
    Get content of Jinja2 template
    :param template_name: template name
    :return content
    """
    template = env.get_template(template_name)
    return template.render(*args, **kwargs)
