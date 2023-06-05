# 1.1.0
Added the `arg_config` property to the template *config.json* file. It lets you specify the arguments that should be passed to the `tempalte build` command. The template build command creates an argument parser based on that property. In order to use the arguments of the template, separate them using double dashes (`--`). For example, `project-template build <template-name> -- --arg1 value1 --arg2 value2`. This also lets you use the `--help` argument to see the arguments of the template (e.g. `project-template build <template-name> -- --help`).

# 1.0.0
Implemented basic template features.

Commands:
- `project-template list` - lists all of the tempaltes and their descriptions
- `project-template build <template-name>` - creates files based on the tempalte

The *config.json* file properties:
- `description` - the description of the template used in the `template list` command
- `can_override` - a list of glob patterns to the files that can be overriden
- `python_code_start` - a starting symbol for replacing the content of the files with generated data
- `python_code_end` - an ending symbol for replacing the content of the files with generated data
- `can_execute` - a list of files that can execute python code between the `python_code_start` and `python_code_end` symbols in order to generate the content of the file

