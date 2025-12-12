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

        Args;
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

        Args;
            file_path (str): the path to the file

            from_line (int): first line to be replaced

            to_line (int): last line to be replaced

            content (str): content to insert in place of the deleted lines

        Returns:
            Does not return extra information.
        """
        cmd = f'cat {file_path}'
        lines = self.run_bash_cmd(cmd)
        # Calculate 0-indexed positions

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

        Args;
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
        """
        cmd = f'cat -n "{file_path}"'
        return self.run_bash_cmd(cmd)
    
    def show_files(self, file_paths: list[str]) -> str:
        """
        Show the contents of each file in the given list of file paths

        Args;
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
        Return a list of files which contain the given content string
        """

        cmd = f'grep -Rn "{content}" || true'
        return self.run_bash_cmd(cmd)
    
    def find_references_in_file(self, file_path: str, content: str):
        """
        Return a list of all line numbers and instances in the given file where the given content appears
        """
        cmd = f'grep -n "{content}" {file_path}'
        return self.run_bash_cmd(cmd)

class DumbEnvironment:
    """
    Dumb environment that just executes the command
    """

    def execute(self, command: str) -> str:
        """
        Run the command in bash and return the output

        Args;
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

        Args;
            command (str): the shell command to run

        Returns:
            The output of running the shell command
        """
        return self.execute(command)
