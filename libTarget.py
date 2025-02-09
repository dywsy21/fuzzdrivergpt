import os
import re
import copy
import pickle
from pathlib import Path

try:
    import yaml
except Exception as ex:
    print('[WARN] package yaml not found, assume we are in the container header/validation stage, keep execution')

class TargetCfg:

    def __init__(self, basedir, cfgs=None, build_cfgs_yml=None, target=None, task_idx=None, workdir=None):
        #
        # task_idx is used for unique naming in parallel scenario
        #
        # load build cfgs
        if (cfgs != None and build_cfgs_yml != None) or (cfgs == None and build_cfgs_yml == None):
            raise Exception('error constructor usage for TargetCfg')

        if cfgs != None:
            self.cfgs = cfgs
            if target == None:
                raise Exception('missing target for directly passing cfg construction')

        else:
            with open(build_cfgs_yml, 'r') as f:
                build_cfgs = yaml.safe_load(f)
                #print(build_cfgs)
                self.cfgs = build_cfgs['targets'][target]

        self.language = self.cfgs['language'].lower()
        self.target = target
        self.basedir = os.path.abspath(basedir)
        if workdir == None:
            self.workdir = os.path.join(self.basedir, 'targets', self.target, self.language, ('para-%s' % (str(task_idx))) if task_idx != None else 'solo')
        else:
            self.workdir = workdir
        self.cachedir = os.path.join(self.basedir, 'targets', self.target, self.language, 'cache')

        # Handle empty lists/dicts for optional fields
        self.apiblocklist = self.cfgs.get('apiblocklist', [])
        self.headerdict = self.cfgs.get('headers', {})
        self.binaries = self.cfgs.get('binaries', [])
        self.imagename = self.cfgs.get('imagename', 'fuzzbuntu')
        self.precode = eval('"""' + (self.cfgs.get('precode', '') or '') + '"""')

        # Language specific configurations
        if self.language == 'c' or self.language == 'cpp':
            if 'autoinclude' not in self.cfgs:
                self.autoinclude = True
            else:
                self.autoinclude = self.cfgs['autoinclude']
            
            # C/C++ specific file extensions
            if self.language == 'c':
                self.outfile = os.path.join(self.workdir, 'dummyfuzzer.c')
                self.testfile = os.path.join(self.workdir, 'dummytester.c')
            else:  # cpp
                self.outfile = os.path.join(self.workdir, 'dummyfuzzer.cc')
                self.testfile = os.path.join(self.workdir, 'dummytester.cc')
        
        elif self.language == 'javascript':
            self.outfile = os.path.join(self.workdir, 'fuzz.js')
            self.testfile = os.path.join(self.workdir, 'test.js')
        
        elif self.language == 'python':
            self.outfile = os.path.join(self.workdir, 'fuzz.py')
            self.testfile = os.path.join(self.workdir, 'test.py')
        
        else:
            raise Exception('unsupported language %s for target %s' % (self.language, self.target))

        # Common paths for all languages
        self.validatepickle = os.path.join(self.workdir, 'validate.pickle')
        self.statusfile = os.path.join(self.workdir, 'status.txt')
        self.outexe = os.path.join(self.workdir, 'dummyfuzzer')  # Keep for compatibility
        self.logfile = os.path.join(self.workdir, 'build.log')
        self.fuzzlog = os.path.join(self.workdir, 'fuzz.log')
        self.artifactdir = os.path.join(self.workdir, 'artifact')
        self.seeddir = os.path.join(self.workdir, 'seeds')
        self.headerpickle = os.path.join(self.workdir, 'header.pickle')
        self.headerparampickle = os.path.join(self.workdir, 'headerparam.pickle')
        self.projanaresult = os.path.join(self.workdir, 'proj_analyzer_result.json')
        self.apiusagecache = os.path.join(self.cachedir, 'apiusages.json')
        self.sgusagejson = os.path.join(self.cachedir, 'sgusage.json')

        # Build and run commands based on language
        if self.language in ['c', 'cpp']:
            self.compileopts = self.cfgs.get('compile', [])
            # Standard C/C++ compiler options
            self.compileopts.extend([
                '-Wno-unused-variable',
                '-Wno-newline-eof',
                '-Wno-unused-but-set-variable',
                '-Wno-implicit-function-declaration'
            ])
            self.buildcmd = self.cfgs['build'].replace('COMPBASE', ' '.join(self.compileopts)).replace('OUTFILE', self.outfile).replace('OUTEXE', self.outexe)

            # CPP specific build commands if available
            if 'compile_cpp' in self.cfgs and 'build_cpp' in self.cfgs:
                self.compileopts_cpp = self.cfgs['compile_cpp']
                self.compileopts_cpp.extend([
                    '-Wno-unused-variable',
                    '-Wno-newline-eof',
                    '-Wno-unused-but-set-variable',
                    '-Wno-implicit-function-declaration'
                ])
                self.buildcmd_cpp = self.cfgs['build_cpp'].replace('COMPBASE', ' '.join(self.compileopts_cpp)).replace('OUTFILE', self.outfile).replace('OUTEXE', self.outexe)
        else:
            # For JS/Python, no compilation needed
            self.compileopts = []
            self.buildcmd = ""

        # Run command setup
        self.runcmd = self.cfgs.get('run', '').replace('OUTEXE', self.outexe).replace('ARTIFACTDIR', self.artifactdir).replace('SEEDDIR', self.seeddir)
        self.fuzzsh = "/tmp/fuzz.sh"
        self.runcmd_subprocess = ["bash", "-x", "/tmp/fuzz.sh"]

        # Test-specific paths and commands
        self.testcase = os.path.join(self.workdir, 'testcase')
        self.testexe = os.path.join(self.workdir, 'dummytester')
        self.testlog = os.path.join(self.workdir, 'test.log')
        
        if self.language in ['c', 'cpp']:
            self.testbuildcmd = self.cfgs['build'].replace('COMPBASE', ' '.join(self.compileopts)).replace('OUTFILE', self.testfile).replace('OUTEXE', self.testexe).replace('-fsanitize=fuzzer-no-link', '').replace('-fsanitize=fuzzer', '')
        else:
            self.testbuildcmd = ""

        self.known_drivers = self.cfgs.get('known_drivers', [])

    def getOutTreeBuildCmd(self, outfile, outexe):
        if self.language in ['javascript', 'python']:
            return ""  # No build command needed for interpreted languages
        return self.cfgs['build'].replace('COMPBASE' ,' '.join(self.compileopts)).replace('OUTFILE', outfile).replace('OUTEXE', outexe)

    def getOutTreeBuildCmdCpp(self, outfile, outexe):
        if self.language in ['javascript', 'python']:
            return ""  # No build command needed for interpreted languages
        return self.cfgs['build_cpp'].replace('COMPBASE' ,' '.join(self.compileopts_cpp)).replace('OUTFILE', outfile).replace('OUTEXE', outexe)

    @staticmethod
    def pickleTo(frm, picklepath):
        obj = copy.deepcopy(frm)
        obj.docker = None
        with open(picklepath, 'wb') as f:
            pickle.dump(obj, f)

    @staticmethod
    def pickleFrom(to):
        with open(to, 'rb') as f:
            obj = pickle.load(f)
            return obj

    def get_header_files(self):
        files = {}

        for prefix, pattern in self.headerdict.items():
            absprefix = str(Path(prefix).resolve())
            for p in Path(prefix).glob(pattern):
                if p.is_file():
                    absfile = p.resolve()
                    absfile = str(absfile)
                    #print('absfile %s' % (absfile))
                    if absfile in files:
                        #pick the most specific prefix if there is one more prefix for this file
                        if len(files[absfile]) < len(absprefix):
                            files[absfile] = absprefix
                    else:
                        files[absfile] = absprefix

        return files

    def validateFuzzDriver(self, driverstr, checkcompile=True):
        """
        Return (True, "") if the driver is valid
        Return (False, error_message) if the driver is invalid
        """
        if not os.path.exists(self.workdir):
            os.makedirs(self.workdir)

        # Setup output file based on language
        if self.language == 'javascript':
            driver_file = os.path.join(self.workdir, 'fuzz.js')
            test_cmd = 'node --check'
        elif self.language == 'python':
            driver_file = os.path.join(self.workdir, 'fuzz.py') 
            test_cmd = 'python3 -m py_compile'
        else:
            driver_file = os.path.join(self.workdir, 'fuzz.c')
            test_cmd = None

        # Write driver content
        with open(driver_file, 'w') as f:
            f.write(driverstr)

        # Create seeds directory if needed
        seedsdir = os.path.join(self.workdir, 'seeds')
        if not os.path.exists(seedsdir):
            os.makedirs(seedsdir)
            with open(os.path.join(seedsdir, 'seed1'), 'w') as f:
                f.write('fuzzing')

        if not checkcompile:
            return True, ""

        # Language specific validation
        if self.language == 'javascript':
            # Check JS syntax
            ret = os.system(f"{test_cmd} {driver_file}")
            if ret != 0:
                return False, "JavaScript syntax validation failed"

            # Verify required fuzzing imports
            if '@jazzer.js/core' not in driverstr:
                return False, "Missing required jazzer.js import"
            
            if 'module.exports.fuzz' not in driverstr:
                return False, "Missing fuzz function export"

        elif self.language == 'python':
            # Check Python syntax
            ret = os.system(f"{test_cmd} {driver_file}")
            if ret != 0:
                return False, "Python syntax validation failed"

            # Verify required fuzzing imports and functions
            if 'import atheris' not in driverstr:
                return False, "Missing required atheris import"
            
            if 'TestOneInput' not in driverstr:
                return False, "Missing TestOneInput function"

        else:
            # Existing C/C++ validation logic
            if not os.path.exists(self.artifactdir):
                os.makedirs(self.artifactdir)

            # Build the test driver
            buildcmd = self.buildcmd
            if self.language == 'cpp':
                buildcmd = self.buildcmd_cpp
            
            ret = os.system('%s >%s 2>&1' % (buildcmd, self.logfile))
            if ret != 0:
                with open(self.logfile, 'r') as f:
                    log = f.read()
                return False, "Build failed: %s" % log

        return True, ""
