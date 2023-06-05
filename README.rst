Project template
================

Python module with a script for generating new projects of any kind with a predefined structure.

This project is basically an automated copy-paste tool with an option to replace some parts of the copied files with the code generated in Python.

**Warning: Running templates executes Python scripts from that template.**

**Warning: The script works on files directly in the working directory. If it crashes, it can leave the files in the working directory in an inconsistent state.**

The application files are stored in usef files in path generated using `Appdirs <https://pypi.org/project/appdirs/>`_ module in:

.. code-block:: python

    Path(appdirs.user_data_dir('nusiq-project-template'))

The templates are in the `templates` subdirectory.

.. code-block:: python

    Path(appdirs.user_data_dir('nusiq-project-template', 'templates'))

Using the commandline tool
--------------------------
Project template is intended to be used as a commandline tool. In order to create new files based on a tepmlate simply run:

.. code-block:: python

    project-template build <template_name>

In order to list available templates you can run:

.. code-block:: python

    project-template list

The process of creating templates is described below in the *Template Structure* section of the documentation.

Template structure
------------------

A template is a directory in the `templates` that follow the structure:

.. code-block:: python

    templates
    ├── template_name
    │   ├── files
    │   │   ├── file1
    │   │   ├── file2
    │   │   └── file3
    │   └── config.json

- :code:`template_name` - is used to identify the tempalte. This name is used as the first command line argument to specify which template to use.
- :code:`config.json` - a JSON file with the template configuration.
- :code:`files` - the files of the template. These files are copied to the working directory of the execution of the commandline tool.

The *config.json* file
----------------------

The *config.json* file is a JSON file with the following structure:

.. code-block:: json

    {
        // The description of the template used when listing the
        // templates in the commandline tool.
        "description": "The description of the template",

        // The list of glob patterns that match the files that can override
        // the files in the working directory.
        //
        // The glob patterns shluld be relative to the "files" foler, not to
        // the root of the template. This means that most of the patterns
        // shoudn't start with "files/".
        "can_override": [
            "glob_pattern1",
            "glob_pattern2"
        ],

        // The symbols that define start and end of the Python code in the text
        // files of the template. The text between these symbols is evaluated
        // as a single Python expression. The expresion must be in a single
        // line.
        "python_code_start": "start_symbol", // default: "<<<"
        "python_code_end": "end_symbol",  // default: ">>>"

        // The list of glob patterns that match the files that can execute
        // the Python code to replace their content.
        //
        // The glob patterns shluld be relative to the "files" foler, not to
        // the root of the template. This means that most of the patterns
        // shoudn't start with "files/".
        "can_execute": [
            "glob_pattern1",
            "glob_pattern2"
        ],

        // The variables that can be used in the Python code inserted into the
        // files of the 
        "scope": {
            "variable1": "value1",
            "variable2": "value2"
        }
    }

- The config file can use comments which is not a standard JSON feature.
- The config file is evaluated using
  `reoglith JSON tempalte <https://pypi.org/project/regolith-json-template/>`_
  module. With the default scope of
  :code:`{"uuid": uuid, "cwd_dir_name": <cwd_dir_name>}` (where :code:`uuid`
  is the Python's :code:`uuid` module and :code:`cwd_dir_name` is the name of
  the current working directory).
- When using :code:`project-template list` command, the *config.json* file is not
  evaluated so you can't create dynamic descriptions of the templates.

Evaluating the Python code in the files
---------------------------------------

You can insert dynamic content into the files of the template by adding the
files to be evaluated to the :code:`can_execute` list in the *config.json* and
than inserting the Python code between the :code:`python_code_start` and
:code:`python_code_end` symbols.

The the inserted Python code is evaluated and the result is inserted into the
file.

**Exmple:**

.. code-block::

    This is a file with some text.
    UUID: <<<uuid.uuid4()>>>
    CWD dir name: <<<cwd_dir_name>>>

    This is the end of the file.

**Result:**
The reult asumes that the current working directory is named :code:`my_project`.

.. code-block::

    This is a file with some text.
    UUID: 7385cffe-f0cb-444b-bdee-d97473a6d9ef
    CWD dir name: my_project

    This is the end of the file.
