from collections import OrderedDict
from pathlib import Path
from subprocess import CompletedProcess, DEVNULL, PIPE
from unittest import main, TestCase
from unittest.mock import MagicMock, Mock, patch

from simple_test.runner import run_simple_scanner, run_simple_cst, \
    run_simple_symbol_table


PREFIX = 'simple_test.runner'


class TestRunner(TestCase):
    def test_run_simple_scanner(self):
        self.assertRunsSimple(run_simple_scanner, ['-s'])

    def test_run_simple_cst(self):
        self.assertRunsSimple(run_simple_cst, ['-c'])

    def test_run_simple_symbol_table(self):
        self.assertRunsSimple(run_simple_symbol_table, ['-t'])

    def assertRunsSimple(self, runner, args):
        with patch("{}.run".format(PREFIX)) as self.subprocess_run, \
             patch("{}.shell_quote".format(PREFIX)) as self.shell_quote, \
             patch("{}.environ".format(PREFIX), new={}) as self.environ:

            for raises in (False, True):
                self.assertRunsSimpleWithArgument(runner, args,
                                                  relative_to_raises=raises)
                self.assertRunsSimpleWithArgument(runner, args,
                                                  sc_path='./foo',
                                                  relative_to_raises=raises)
                self.assertRunsSimpleAsStdin(runner, args,
                                             relative_to_raises=raises)
                self.assertRunsSimpleAsStdin(runner, args, sc_path='./foo',
                                             relative_to_raises=raises)

    def setup_subprocess(self, sc_path=None, relative_to_raises=False):
        sim_file = MagicMock()
        sim_file.__str__.return_value = 'non_relative_path.sim'
        relative_sim_file = MagicMock()
        relative_sim_file.__str__.return_value = 'foo/bar.sim'

        if not relative_to_raises:
            cwd = Path('.').resolve()

            sim_file.relative_to.side_effect = \
                lambda p: relative_sim_file if p == cwd else None
        else:
            sim_file.relative_to.side_effect = ValueError('relative_to')

        stdout, stderr = Mock(), Mock()
        fake_args = ('a', 'b')
        quoted_args = OrderedDict([('a', 'c'), ('b', 'd')])
        completed_process = Mock(CompletedProcess, args=fake_args,
                                 stdout=stdout, stderr=stderr)

        if sc_path:
            self.environ['SC'] = sc_path
        elif 'SC' in self.environ:
            del self.environ['SC']

        self.subprocess_run.reset_mock()
        self.shell_quote.reset_mock()
        self.subprocess_run.return_value = completed_process
        self.shell_quote.side_effect = lambda x: quoted_args[x]

        cmd = ' '.join(quoted_args.values())

        return sim_file, relative_sim_file, cmd, stdout, stderr

    def assertRunsSimpleWithArgument(self, runner, args, sc_path=None,
                                     relative_to_raises=False):
        sim_file, relative_sim_file, cmd, stdout, stderr = \
            self.setup_subprocess(sc_path, relative_to_raises)
        last_arg = sim_file if relative_to_raises else relative_sim_file

        result = runner(sim_file)

        self.subprocess_run \
            .assert_called_once_with([sc_path if sc_path else './sc', *args,
                                      str(last_arg)], stdout=PIPE,
                                     stderr=PIPE, stdin=DEVNULL)
        self.assertEqual(cmd, result.cmd)
        self.assertEqual(stdout, result.stdout)
        self.assertEqual(stderr, result.stderr)

    def assertRunsSimpleAsStdin(self, runner, args, sc_path=None,
                                relative_to_raises=False):
        sim_file, relative_sim_file, cmd, stdout, stderr = \
            self.setup_subprocess(sc_path, relative_to_raises)
        redirected_file = sim_file if relative_to_raises else relative_sim_file

        # Wire up relative_sim_file so we can call .open() on it
        fake_file = MagicMock()
        fake_file_context = MagicMock()
        fake_file_context.__enter__.return_value = fake_file
        redirected_file.open.return_value = fake_file_context

        result = runner(sim_file, as_stdin=True)

        redirected_file.open.assert_called_once_with()
        self.subprocess_run \
            .assert_called_once_with([sc_path if sc_path else './sc', *args],
                                     stdout=PIPE, stderr=PIPE, stdin=fake_file)
        self.assertEqual("{} < {}".format(cmd, redirected_file), result.cmd)
        self.assertEqual(stdout, result.stdout)
        self.assertEqual(stderr, result.stderr)


if __name__ == '__main__':
    main()
