"""scripts/nup_probe.py, the survey of a .nup whose title has no profile yet, run as a user runs it (a subprocess) against a synthetic .nup
(test_nup.py's fixtures, --raw so no zstd is needed): the packages listed, the highest update surveyed, the measured build IDs and modules row
in the draft game.tsv, and the upper-case .NUP refused. No game files needed."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'dm/tools/tests'))
import test_nup


def run_probe(*argv):
    return subprocess.run([sys.executable, str(REPO / 'scripts/nup_probe.py'), *argv], capture_output=True, text=True, timeout=300)


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        root = Path(cls.td.name).resolve()
        test_nup.dump(root / 'Game')
        cls.nup = test_nup.write_nup(root / 'Game', root / 'Game.nup', '--raw')
        cls.out = run_probe(str(cls.nup))

    @classmethod
    def tearDownClass(cls): cls.td.cleanup()

    def test_packages_and_choice(self):
        self.assertEqual(self.out.returncode, 0, self.out.stderr)
        out = self.out.stdout
        self.assertIn('base\t040074A01BF12000\tv0', out)
        self.assertIn(f'update/{test_nup.VER}\t040074A01BF12000\tv{test_nup.VER}', out)
        self.assertIn(f'surveying: update/{test_nup.VER}', out)   # the highest update, not the base

    def test_version_flag(self):
        r = run_probe(str(self.nup), '--version', str(test_nup.VER))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f'surveying: update/{test_nup.VER}', r.stdout)

    def test_bad_file_refused(self):
        r = run_probe(str(self.nup.with_suffix('.NUP')))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('lower case', r.stdout + r.stderr)

    def test_report_and_draft(self):
        out = self.out.stdout
        self.assertIn('## Code modules', out)
        self.assertIn('| main |', out); self.assertIn('| sdk |', out)
        self.assertRegex(out, r'build\t%d\tmain=[0-9a-f]{32} sdk=[0-9a-f]{32}' % test_nup.VER)   # the game.tsv build row's measured form
        self.assertIn('Draft dm/games/040074A01BF12000/game.tsv', out)
        self.assertIn('modules\tmain sdk', out)   # load_order: main before sdk
        self.assertIn('title_id\t040074A01BF12000', out)
        self.assertIn('program_id\t040074A01BF12000', out)   # the fixture npdm's program ID
        self.assertIn('## RomFS: 7 files', out)
        self.assertIn('[RED] profile_guess.facts_of refused', out)   # the fixture's modules have no MOD0: the fallback's red note
        self.assertIn('TODO: the game\'s name', out)   # a .nup carries no control.nacp


if __name__ == '__main__':
    unittest.main()
