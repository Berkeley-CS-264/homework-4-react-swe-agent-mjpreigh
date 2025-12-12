import ast
from utils import get_sb_environment
import subprocess
import swebench
import tempfile
import os
import tempfile
import subprocess
from pathlib import Path

class LimitsExceeded(Exception):
    """Raised when the agent has reached its step limit."""


class SWEEnvironment:
    """
    Minimal interface to the SWEBench execution environment.

    Students may use their own wrapper. The environment must expose:
    - execute(command: str) -> str: Run a shell command and return stdout, or raise ValueError on failure
    """

    def __init__(self, instance: dict):
        self.env = get_sb_environment(instance)
        self.instance = instance  # Store instance for test execution
     
    # -------------------- REQUIRED TOOLS --------------------
    def run_bash_cmd(self, command: str) -> str:
        """
        Run the command in a bash shell and return the output or throw a ValueError
        if the process returns non-zero exit code.

        Args:
            command (str): the shell command to run

        Returns:
            The output of running the shell command
        """
        try:
            output = self.env.execute(command)
            
            # Handle case where execute returns a dict instead of string
            if isinstance(output, dict):
                output = output.get("output", "") or output.get("stdout", "")
                
        except subprocess.TimeoutExpired as e:
            output = e.output.decode("utf-8", errors="replace") if e.output else ""
            raise ValueError(output)
        except TimeoutError:
            raise ValueError("TimeoutError")
        return output
    
    def generate_patch(self, result: str) -> str:
        """
        Generate a patch from the result (for SWE-Bench)
        """
        try:
            patch_output = self.env.execute("git add -A && git diff --cached")
            
            # Handle case where execute returns a dict instead of string
            if isinstance(patch_output, dict):
                patch_output = patch_output.get("output", "") or patch_output.get("stdout", "")
            
            if patch_output and patch_output.strip():
                return patch_output
            else:
                return f"{result}\n\nNo changes detected to generate a patch."
        except Exception as e:
            return f"{result}\n\nError running git commands: {e}"

    # -------------------- TODO(student): add more functions here if you want, not required --------------------
    # run script
    def replace_in_file(self, file_path: str, from_line: int, to_line: int, content: str) -> str:
        """
        Replace the content of the file from the given line to the given line with the given content. ALL CONTENT ON AND BETWEEN THE GIVEN LINES WILL BE DELETED.

        Args:
            file_path (str): the path to the file

            from_line (int): first line to be replaced

            to_line (int): last line to be replaced

            content (str): content to insert in place of the deleted lines

        Returns:
            Does not return extra information.
        """
        cmd = f'cat {file_path}'
        lines = self.run_bash_cmd(cmd)

        line_num = 1
        new_lines = []
        for line in lines.splitlines():
            if line_num < int(from_line) or line_num > int(to_line):
                new_lines.append(line)
            if line_num == from_line:
                content_lines = content.splitlines("/n")
                print("content start")
                for line2 in content_lines:
                    print(line2)
                    new_lines.append(line2)
                print("content end")
            line_num += 1

        print("start new lines")
        line_num = 1
        for linen in new_lines:
            print(linen)
            cmd = f'echo "{linen}" > {file_path}'
            if line_num > 1:
                cmd = f'echo "{linen}" >> {file_path}'
            self.run_bash_cmd(cmd)
            line_num += 1

        print("end new lines")
        return self.show_file(file_path)

    
    def insert_in_file(self, file_path: str, line_number: int, content: str) -> str:
        """
        Insert the given content in the file after the given line number. NOTHING WILL BE DELETED FROM THE FILE.

        
            file_path (str): the path to the file

            line_number (int): the content will be inserted AFTER this line number

            content (str): content to insert in place of the deleted lines

        Returns:
            Does not return extra information.
        """
        line_number = int(line_number)

        cmd = f'head -n {line_number} {file_path} > temp_file.txt'
        self.run_bash_cmd(cmd)
        cmd = f'echo {content} >> temp_file.txt'
        self.run_bash_cmd(cmd)
        cmd = f'tail -n +{line_number + 1} {file_path} >> temp_file.txt'
        self.run_bash_cmd(cmd)
        cmd = f'cat temp_file.txt > {file_path}'
        self.run_bash_cmd(cmd)
        return "Now run tests to see if the is a successful patch. (Command might be ./tests/runtests.py, pytest -q, or something else)"


    def show_file(self, file_path: str) -> str:
        """
        [Optional]Show the content of the file

        Args:
            file_path (str): file path

        Returns:
            The contents of the given file
        """
        cmd = f'cat -n "{file_path}"'
        return self.run_bash_cmd(cmd)
    
    def show_files(self, file_paths: list[str]) -> str:
        """
        Show the contents of each file in the given list of file paths

        Args:
            file_paths (list[str]): a list of file paths

        Returns:
            The contents of each file in the given list
        """
        file_paths = ast.literal_eval(file_paths)
        results = []
        for file in file_paths:
            print("file: " + file)
            results.append(f'-----FILE: "{file}"-----')
            results.append(self.show_file(file))

        res = "\n".join(results)
        print("shown files: " + res)
        return res
    
    def search_files(self, content: str) -> str:
        """
        Return a list of files which contain the given content string, and the snippet of code of each instance.

        Args:
            content (str): The string to look for in files.

        Returns:
            List of file paths containing files where the given string shows up, and the snippet of code of each instance.
        """
        #cmd = 'grep -r -l "{Show the contents of each file in the given list of file paths}" .'
        num_results = 20          # number of results to show
        print("here 1")

        cmd = (
            f"grep -RIn --include='*.py' "
            f"--exclude-dir='.*' "
            f"--exclude-dir='__pycache__' "
            f"--exclude-dir='node_modules' "
            f"-C5 '{content}' | head -n {num_results}"
        )
        res = self.run_bash_cmd(cmd)
        print("search res: " + str(res))
        #return res
        results = []

        #cmd = f'grep -Rl "{content}"'
        #return self.run_bash_cmd(cmd)
        files = self.run_bash_cmd(cmd).strip().split('\n')

        if files[0] == '':
            files = []
        for file in files:
            if file[0] == "." or file == '':
                continue
            results.append(f'-----FILE: {file}-----')

            cmd = f'grep -n "{content}" {file} | awk -F: \'{{print $1}}\''

            lines = self.run_bash_cmd(f'grep -n "{content}" {file} | awk -F: \'{{print $1}}\'')

            lines = lines.strip().split('\n')
            print("here 1")
            print("lines: " + str(lines))
            for line in lines:
                print("line: " + line)
                if not line.isnumeric():
                    continue
                if int(line) > 2:
                    minus = int(line) - 2
                    line_text = self.run_bash_cmd(f'sed -n \'{int(minus)}p\' {file}')
                    results.append(f'{minus}: {line_text}')
                if int(line) > 1:
                    minus = int(line) - 1
                    line_text = self.run_bash_cmd(f'sed -n \'{int(minus)}p\' {file}')
                    results.append(f'{minus}: {line_text}')
                line_text = self.run_bash_cmd(f'sed -n \'{int(line)}p\' {file}')
                results.append(f'{line}: {line_text}')
                plus = int(line) + 1
                line_text = self.run_bash_cmd(f'sed -n \'{int(plus)}p\' {file}')
                results.append(f'{plus}: {line_text}')
                plus = int(line) + 2
                line_text = self.run_bash_cmd(f'sed -n \'{int(plus)}p\' {file}')
                results.append(f'{plus}: {line_text}')
        results = "\n".join(results)
        print("results: " + results)
        return results
    
    def find_references_in_file(self, file_path: str, content: str) -> str:
        """
        Return a list of all line numbers and instances in the given file where the given content appears. Includes context of line before and after the instance.

        Args:
            file_path (str): The file to look in

            content (str): The string to look for in the file

        Returns:
            List of the line numbers and specific text where the content shows up in the file.  Includes context of line before and after the instance.
        """
        cmd = f'grep -n "{content}" {file_path}'
        return self.run_bash_cmd(cmd)
    

    def find_all_imports_in_file(self, file_path: str) -> str:
        """
        Return all imports in file.

        Args:
            file_path (str): The file to look in

        Returns:
        List of imports in file
        """
        res = self.find_references_in_file(file_path, "import")
        print("imports: " + res)
        return res
    
    def list_python_files(self) -> str:
        """
        Return list of all python files.
        """
        cmd = 'find . -type f -name "*.py"'
        res = self.run_bash_cmd(cmd)
        print("all files: " + res)
        return res
    
    def list_uncommitted_python_files(self) -> str:
        """
        Return list of all uncommitted python files. Use this to find recently edited documents.
        """
        cmd = 'git status --porcelain | grep \'\.py$\' | awk \'{print $2}\''
        res = self.run_bash_cmd(cmd)
        print("all uncommitted files: " + res)
        return res
    
    def list_broken_python_files(self) -> str:
        """
        Return list of all python files containing TODO or FIXME comments. Use this to find incomplete code that is causing bugs.
        """
        cmd = 'grep -Rn -E \'TODO|FIXME\' --include="*.py" .'
        res = self.run_bash_cmd(cmd)
        return res
    
    def functions_per_python_file(self) -> str:
        """
        List number of functions in each Python file. Use to identify hotspots of functionality. Bugs are likely there.
        """
        cmd = 'grep -R -c \'^def \' --include="*.py" .'
        res = self.run_bash_cmd(cmd)
        return res
    
    def find_test_files(self) -> str:
        """
        Lists test files. Use this to identify tests to run in order to find buggy code and verify edits.
        """
        cmd = 'find . -type f -name "test_*.py"'
        res = self.run_bash_cmd(cmd)
        return res

    
    def run_script(self, script: str) -> str:
        """
        Return the results of running the given Python script

        Args:
            script (str): Python script to run

        Returns:
            Output from running the given Python script
        """
        cmd = f'python3 - << \'PY\'\n{script}'
        print("to run: " + cmd)
        return self.run_bash_cmd(cmd)

    def delete_lines(self, file_path: str, from_line: int, to_line: int) -> str:
        """
        Delete lines from file between and including from_line and to_line

        Args:
            file_path (str): File to delete lines from

            from_line (int): First line to delete

            to_line (int): Last linen to delete


        Returns:
            Contents of the file after lines deleted
        """
        cmd = f'cat {file_path}'
        lines = self.run_bash_cmd(cmd)
        # Calculate 0-indexed positions

        line_num = 1
        new_lines = []
        for line in lines.splitlines():
            if line_num < int(from_line) or line_num > int(to_line):
                new_lines.append(line)
            line_num += 1

        print("start new lines")
        line_num = 1
        for linen in new_lines:
            print(linen)
            cmd = f'echo "{linen}" > {file_path}'
            if line_num > 1:
                cmd = f'echo "{linen}" >> {file_path}'
            self.run_bash_cmd(cmd)
            line_num += 1

        print("end new lines")
        return self.show_file(file_path)

class DumbEnvironment:
    """
    Dumb environment that just executes the command
    """

    def execute(self, command: str) -> str:
        """
        Run the command in bash and return the output

        Args:
            command (str): the shell command to run

        Returns:
            The output of running the shell command
        """
        result = subprocess.run(command, capture_output=True, shell=True, check=False)
        output = f"--STDOUT--\n{result.stdout.decode()}\n--STDERR--\n{result.stderr.decode()}"
        if result.returncode:
            raise ValueError(output)
        return output
    
    def run_bash_cmd(self, command: str) -> str:
        """
        Run the command in a bash shell and return the output or throw a ValueError
        if the process returns non-zero exit code.

        Args:
            command (str): the shell command to run

        Returns:
            The output of running the shell command
        """
        return self.execute(command)
