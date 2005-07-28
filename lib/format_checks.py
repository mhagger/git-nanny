"""Check conformance to whitespace rules."""

import sys
import re


# The string that is used as a marker for "don't check me in!".  This
# has to be written strangely to allow this file itself to be checked
# in.
MARKER_STRING = '@''@''@'


class Check:
    """A check that can be applied to a file."""

    def __call__(self, file):
        """Return True iff file passes test."""

        return 1


class TrailingWhitespaceCheck(Check):
    """Don't allow whitespace at the end of a line or the end of the file."""

    trailing_ws_re = re.compile(r'[ \t]+$', re.MULTILINE)

    def __init__(self):
        pass

    def __call__(self, file):
        if self.trailing_ws_re.search(file.get_text()):
            sys.stderr.write('Trailing whitespace in %s\n' % (file,))
            return False
        else:
            return True


class LeadingWhitespaceCheck(Check):
    """Don't allow whitespace at the start of a line."""

    trailing_ws_re = re.compile(r'^[ \t]', re.MULTILINE)

    def __call__(self, file):
        if self.trailing_ws_re.search(file.get_text()):
            sys.stderr.write('Trailing whitespace in %s\n' % (file,))
            return False
        else:
            return True


class BlankLineCheck(Check):
    """Don't allow lines that are completely empty."""

    blank_line_re = re.compile(r'^\n', re.MULTILINE)

    def __call__(self, file):
        if self.blank_line_re.search(file.get_text()):
            sys.stderr.write('Blank line in %s\n' % (file,))
            return False
        else:
            return True


class TabCheck(Check):
    """Don't allow any tab characters."""

    def __call__(self, file):
        if file.get_text().find('\t') != -1:
            sys.stderr.write('Tab(s) in %s\n' % (file,))
            return False
        else:
            return True


class CRCheck(Check):
    """Don't allow any carriage returns characters."""

    def __call__(self, file):
        if file.get_text().find('\r') != -1:
            sys.stderr.write('Carriage return(s) in %s\n' % (file,))
            return False
        else:
            return True


class UnterminatedLineCheck(Check):
    """Don't allow the last line to be unterminated."""

    def __call__(self, file):
        text = file.get_text()
        if text and text[-1] != '\n':
            sys.stderr.write('Last line of %s is unterminated\n' % (file,))
            return False
        else:
            return True


class MarkerStringCheck(Check):
    """Don't allow files to be checked in if they include the marker string.

    This string can be used to mark things that you don't ever want
    checked in.  That way Subversion helps you remember :-)

    """

    def __call__(self, file):
        if file.get_text().find(MARKER_STRING) != -1:
            sys.stderr.write(
                'Marker string ("%s") found in %s\n'
                % (MARKER_STRING, file,)
                )
            return False
        else:
            return True


class MultipleCheck(Check):
    """Apply the listed checks one after the other.

    checks should be a sequence of Check objects.

    """

    def __init__(self, *checks):
        self.checks = checks

    def __call__(self, file):
        retval = True
        for check in self.checks:
            if not check(file):
                retval = False

        return retval


class PatternCheck(Check):
    """Apply the specified check to all files whose names match regexp.

    regexp -- a regexp pattern which is passed to re.match().

    check -- a Check object.

    """

    def __init__(self, regexp, check):
        self.regexp = re.compile(regexp)
        self.check = check

    def __call__(self, file):
        if self.regexp.match(file.filename):
            return self.check(file)
        else:
            return True


thoroughcheck = MultipleCheck(
    TrailingWhitespaceCheck(),
    TabCheck(),
    CRCheck(),
    UnterminatedLineCheck(),
    MarkerStringCheck(),
    )

allchecks = MultipleCheck(
    # Java source files:
    PatternCheck(r'.*\.java$', thoroughcheck),

    # Python/Jython source files:
    PatternCheck(r'.*\.py$', thoroughcheck),

    # C/C++ source files:
    PatternCheck(r'.*\.(c|cc|cpp|h)$', thoroughcheck),

    # Java properties files:
    PatternCheck(r'.*\.properties$', thoroughcheck),

    # RPM spec files:
    PatternCheck(r'.*\.spec$', thoroughcheck),

    # Makefile-like files:
    PatternCheck(r'Makefile(\.module)?$', MultipleCheck(
        TrailingWhitespaceCheck(),
        CRCheck(),
        UnterminatedLineCheck(),
        MarkerStringCheck(),
        )),

    # Text files:
    PatternCheck(r'.*\.txt$', MultipleCheck(
        TrailingWhitespaceCheck(),
        CRCheck(),
        UnterminatedLineCheck(),
        MarkerStringCheck(),
        )),
    )


