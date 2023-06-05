import json
import uuid
import math
from pathlib import Path
from typing import Any
import argparse
from textwrap import dedent
from functools import cached_property, cache
import shutil
import sys


import appdirs
from better_json_tools import load_jsonc
from better_json_tools.compact_encoder import CompactEncoder
from better_json_tools.json_walker import JSONWalker
from regolith_json_template import eval_json

VERSION = (1, 1, 0)
__version__ = '.'.join([str(x) for x in VERSION])

ARG_TYPE_MAP = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool
}

class NusiqProjectTemplateError(Exception):
    '''Base class for all errors raised by this package'''

@cache
def get_app_path():
    result = Path(appdirs.user_data_dir()) / 'nusiq-project-template'
    print("The app path is:", result.as_posix())
    return result

def get_templates_path():
    return get_app_path() / 'templates'

def print_red(text: str):
    print('\033[91m' + text + '\033[0m')

def print_yellow(text: str):
    print('\033[93m' + text + '\033[0m')

class TemplateConfig:
    default_scope = {
        'uuid': uuid,
        'math': math
    }
    
    def __init__(
            self,
            files_path: Path,
            can_override: list[str],
            python_code_start: str,
            python_code_end: str,
            can_execute: list[str],
            scope: dict[str, Any]):
        if python_code_start == "":
            raise NusiqProjectTemplateError(
                'The value for "python_code_start" cannot be empty.')
        if python_code_end == "":
            raise NusiqProjectTemplateError(
                'The value for "python_code_end" cannot be empty.')
        self.files_path = files_path
        self._can_override = can_override
        self.python_code_start = python_code_start
        self.python_code_end = python_code_end
        self._can_execute = can_execute
        self.scope = scope

    @staticmethod
    def from_path_and_args(path: Path, args: list[str]):
        '''
        Creates TemplateConfig object from the path to the config.json file and
        the arguments passed to the program.
        '''
        data_walker = load_jsonc(path)
        scope = (
            TemplateConfig.default_scope | {'cwd_dir_name': Path.cwd().name})
        
        data_walker = JSONWalker(eval_json(data_walker.data, scope))

        def _get_list_str_property(list_str_prop_name: str) -> list[str]:
            walker = data_walker / list_str_prop_name
            if walker.exists:
                if not isinstance(walker.data, list):
                    raise NusiqProjectTemplateError(dedent(f'''\
                        Invalid value for "{list_str_prop_name}".
                        Path: {path.as_posix()}
                        JSON path: {walker.path_str}
                        '''))
                for item in walker.data:
                    if not isinstance(item, str):
                        raise NusiqProjectTemplateError(dedent(f'''\
                            Invalid value for "{list_str_prop_name}".
                            Path: {path.as_posix()}
                            JSON path: {walker.path_str}
                            '''))
                return walker.data
            return []

        def _get_str_property(str_prop_name: str, default: str):
            walker = data_walker / str_prop_name
            if walker.exists:
                if not isinstance(walker.data, str):
                    raise NusiqProjectTemplateError(dedent(f'''\
                        Invalid value for "{str_prop_name}".
                        Path: {path.as_posix()}
                        JSON path: {walker.path_str}
                        '''))
                return walker.data
            return default

        can_override = _get_list_str_property('can_override')
        can_execute = _get_list_str_property('can_execute')
        python_code_start = _get_str_property('python_code_start', '<<<')
        python_code_end = _get_str_property('python_code_end', '>>>')

        local_scope_walker = data_walker / 'scope'
        if local_scope_walker.exists:
            if not isinstance(local_scope_walker.data, dict):
                raise NusiqProjectTemplateError(dedent(f'''\
                    Invalid value for "scope".
                    Path: {path.as_posix()}
                    JSON path: {local_scope_walker.path_str}
                    '''))
            local_scope = local_scope_walker.data
        else:
            local_scope = {}
        TemplateConfig._load_args(data_walker, local_scope, args)
        scope.update(local_scope)
        return TemplateConfig(
            files_path=path.parent / 'files',
            can_override=can_override,
            python_code_start=python_code_start,
            python_code_end=python_code_end,
            can_execute=can_execute,
            scope=scope
        )
    
    @staticmethod
    def _get_arg_parser(data_walker: JSONWalker) -> argparse.ArgumentParser:
        '''
        Used in from_path_and_args to get the argument parser from the config.
        '''
        parser = argparse.ArgumentParser()
        arg_config_walker = data_walker / 'arg_config'
        if not arg_config_walker.exists:
            return parser
        if not isinstance(arg_config_walker.data, dict):
            raise NusiqProjectTemplateError(dedent(f'''\
                Invalid value for "arg_config".
                JSON path: {arg_config_walker.path_str}
                '''))
        for arg_v_walker in arg_config_walker // str:
            k = arg_v_walker.parent_key
            add_argument_kwargs = {}
            if (default_walker := arg_v_walker / 'default').exists:
                add_argument_kwargs['default'] = default_walker.data
            if (type_walker := arg_v_walker / 'type').exists:
                if type_walker.data not in ARG_TYPE_MAP.keys():
                    raise NusiqProjectTemplateError(dedent(f'''\
                        Invalid value for "type".
                        JSON path: {type_walker.path_str}
                        Allowed values: {", ".join(ARG_TYPE_MAP.keys())}
                        '''))
                add_argument_kwargs['type'] = ARG_TYPE_MAP[type_walker.data]
            if (nargs_walker := arg_v_walker / 'nargs').exists:
                if (
                        not isinstance(nargs_walker.data, int) and
                        nargs_walker.data not in ["?", "*", "+"]):
                    raise NusiqProjectTemplateError(dedent(f'''\
                        The "nargs" property must be an interger or one of '''
                        f'''the following strings: "?", "*", "+".
                        JSON path: {nargs_walker.path_str}
                        '''))
                add_argument_kwargs['nargs'] = nargs_walker.data
            if (help_walker := arg_v_walker / 'help').exists:
                if not isinstance(help_walker.data, str):
                    raise NusiqProjectTemplateError(dedent(f'''\
                        The "help" property must be a string.
                        JSON path: {help_walker.path_str}
                        '''))
                add_argument_kwargs['help'] = help_walker.data
            if (required_walker := arg_v_walker / 'required').exists:
                if not isinstance(required_walker.data, bool):
                    raise NusiqProjectTemplateError(dedent(f'''\
                        The "required" property must be a boolean.
                        JSON path: {required_walker.path_str}
                        '''))
                add_argument_kwargs['required'] = required_walker.data
            parser.add_argument(k, **add_argument_kwargs)
        return parser

    @staticmethod
    def _load_args(data_walker: JSONWalker, scope: dict[str, Any], args: list[str]):
        '''
        Used in from_path_and_args to load the arguments into scope. Modifies
        the scope in place.
        '''
        try:
            parser = TemplateConfig._get_arg_parser(data_walker)
        except NusiqProjectTemplateError as e:
            raise NusiqProjectTemplateError(dedent(f'''\
                Unable to load the "arg_conifg" from the template config file.
                JSON path: {e.json_path}

                This error is caused by the following:
                ''' + str(e)))
        parsed_args = parser.parse_args(args)
        scope.update(vars(parsed_args))
        return

    @cached_property
    def can_override(self) -> set[Path]:
        '''
        Set of the evaluated paths from the template that can override the
        existing files.
        '''
        result = set()
        for glob_pattern in self._can_override:
            for p in self.files_path.glob(glob_pattern):
                result.add(p.relative_to(self.files_path))
        return result
    
    @cached_property
    def can_execute(self) -> set[Path]:
        '''
        Set of the evaluated paths from the template that can be executed.
        '''
        result = set()
        for glob_pattern in self._can_execute:
            for p in self.files_path.glob(glob_pattern):
                result.add(p.relative_to(self.files_path))
        return result
    
    def walk_files(self):
        '''
        Walk and yield all files in the template files.
        '''
        for p in self.files_path.rglob('*'):
            if p.is_dir():
                continue
            yield p.relative_to(self.files_path)

    def eval_line(self, line: str, text_row: int) -> str:
        '''
        Evaluate a line of text.
        '''
        parts: list[str] = []
        in_code = False
        remaining_line = line
        char_index = 0
        while True:
            if in_code:
                split = remaining_line.find(self.python_code_end)
                if split == -1:
                    raise NusiqProjectTemplateError(dedent(f'''\
                        Missing closing tag for python code.
                        Text Row: {text_row}
                        Text Column: {char_index}
                        Line: {line}
                        Opening tag: {self.python_code_start}
                        Closing tag: {self.python_code_end}
                        '''))
                char_index += split + len(self.python_code_end)
                parts.append(str(eval(remaining_line[:split], self.scope)))
                remaining_line = remaining_line[split + len(self.python_code_end):]
                in_code = False
            else:
                split = remaining_line.find(self.python_code_start)
                if split == -1:
                    parts.append(remaining_line)
                    break
                char_index += split + len(self.python_code_start)
                parts.append(remaining_line[:split])
                remaining_line = remaining_line[split + len(self.python_code_start):]
                in_code = True
        return ''.join(parts)

def build_template(template_name: str, skip_conflicts: bool, parser_args: list[str]):
    '''
    Builds the project from the template with the given name in the
    current working directory.
    '''
    template_path = get_templates_path() / template_name
    if not template_path.exists():
        raise NusiqProjectTemplateError(
            f'Template "{template_name}" not found')
    try:
        config = TemplateConfig.from_path_and_args(
            template_path / 'config.json',
            parser_args)
    except NusiqProjectTemplateError as e:
        raise NusiqProjectTemplateError(dedent(f'''\
            Failed to load config.json of template - "{template_name}":
            Path: {template_path.as_posix()}

            The failore was caused by the following error:
            ''') +
            "\n" + str(e)
        )
    for file_path in config.walk_files():
        source = config.files_path / file_path
        target = Path.cwd() / file_path
        def force_copy():
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if target.is_dir():
                    # I don't have time to deal with this. I don't care.
                    raise NusiqProjectTemplateError(dedent(f'''\
                        Cannot override directory with file.
                        Path: {target.as_posix()}
                        '''))
                target.unlink()
            if file_path in config.can_execute:
                with source.open('r', encoding='utf8') as f:
                    target_lines = [
                        config.eval_line(line, i + 1)
                        for i, line in enumerate(f.readlines())
                    ]
                with target.open('w', encoding='utf8') as f:
                    f.writelines(target_lines)
            else:
                shutil.copyfile(source, target)

        if target.exists():
            if file_path in config.can_override:
                force_copy()
            elif skip_conflicts:
                print_yellow(f'File already exists. Skipping: {target.as_posix()}')
                continue
            else:
                raise NusiqProjectTemplateError(dedent(f'''\
                    File already exists.
                    Path: {target.as_posix()}
                    '''))
        else:
            force_copy()
    print(f'Project "{template_name}" created successfully')

def list_templates():
    '''
    Prints a list of all available templates
    '''
    errors: list[str] = []
    descriptions: list[str] = []
    if not get_templates_path().exists():
        raise NusiqProjectTemplateError(dedent(f'''\
            No templates are installed.
            Templates installation path: {get_templates_path().as_posix()}
            '''))
    for template_path in get_templates_path().iterdir():
        config_path = template_path / 'config.json'
        try:
            description_walker = load_jsonc(config_path) / "description"
            description = description_walker.data
            if not description_walker.exists:
                description = "[No description]"
            if not isinstance(description_walker.data, str):
                description = "[Invalid description]"
            description.replace('\n', ' ').replace('\r', '')
        except (OSError, json.JSONDecodeError) as e:
            errors.append(f'{config_path}: {e}')
            continue
        descriptions.append(f'{template_path.name}: {description}')

    if len(descriptions) == 0:
        print_red('No templates found')
    else:
        print('Available templates:')
        for description_walker in descriptions:
            print(f'- {description_walker}')
    if len(errors) > 0:
        print_red('Errors:')
        for error in errors:
            print_red(f'- {error}')

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    parser_build = subparsers.add_parser('build')
    parser_build.add_argument('template_name', type=str)
    parser_build.add_argument('--skip-conflicts', action='store_true')

    parser_list = subparsers.add_parser('list')

    try:
        arg_split = sys.argv.index("--")
    except ValueError:
        arg_split = len(sys.argv)
    main_args, parser_args = sys.argv[1:arg_split], sys.argv[arg_split + 1:]

    # Run
    args = parser.parse_args(main_args)
    try:
        if args.command == 'build':
            build_template(args.template_name, args.skip_conflicts, parser_args)
        elif args.command == 'list':
            list_templates()
        else:
            parser.print_help()
    except NusiqProjectTemplateError as e:
        print_red(str(e))
        sys.exit(1)
