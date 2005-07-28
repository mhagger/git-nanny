"""Check conformance to whitespace rules."""

import sys
import re

import svnlib


# The string that is used as a marker for "don't check me in!".  This
# has to be written strangely to allow this file itself to be checked
# in.
MARKER_STRING = '@''@''@'


class Check:
    """A check that can be applied to a change."""

    def __call__(self, change):
        """Return True iff change passes test."""

        raise NotImplementedError()


class TextCheck(Check):
    """A Check that is purely based on the text of the file."""

    def __call__(self, change):
        if isinstance(change, svnlib.Addition):
            ok = self.check_text(change.get_new_text())
        elif isinstance(change, svnlib.Modification):
            ok = self.check_text(change.get_new_text())
        else:
            ok = True

        if not ok:
            sys.stderr.write(self.error_fmt % {'filename' : change.file})

        return ok

    def check_text(self, text):
        """Return True iff text is OK."""

        raise NotImplementedError()


class TrailingWhitespaceCheck(TextCheck):
    """Don't allow whitespace at the end of a line or the end of the file."""

    trailing_ws_re = re.compile(r'[ \t]+$', re.MULTILINE)

    error_fmt = 'Trailing whitespace in %(filename)s\n'

    def __init__(self):
        pass

    def check_text(self, text):
        return not self.trailing_ws_re.search(text)


class LeadingWhitespaceCheck(TextCheck):
    """Don't allow whitespace at the start of a line."""

    trailing_ws_re = re.compile(r'^[ \t]', re.MULTILINE)

    error_fmt = 'Leading whitespace in %(filename)s\n'

    def check_text(self, text):
        return not self.trailing_ws_re.search(text)


class BlankLineCheck(TextCheck):
    """Don't allow lines that are completely empty."""

    blank_line_re = re.compile(r'^\n', re.MULTILINE)

    error_fmt = 'Blank line in %(filename)s\n'

    def check_text(self, text):
        return not self.blank_line_re.search(text)


class TabCheck(TextCheck):
    """Don't allow any tab characters."""

    error_fmt = 'Tab(s) in %(filename)s\n'

    def check_text(self, text):
        return text.find('\t') == -1


class CRCheck(TextCheck):
    """Don't allow any carriage returns characters."""

    error_fmt = 'Carriage return(s) in %(filename)s\n'

    def check_text(self, text):
        return text.find('\r') == -1


class UnterminatedLineCheck(TextCheck):
    """Don't allow the last line to be unterminated."""

    error_fmt = 'Last line of %(filename)s is unterminated\n'

    def check_text(self, text):
        return (not text) or text[-1] == '\n'


class MarkerStringCheck(TextCheck):
    """Don't allow files to be checked in if they include the marker string.

    This string can be used to mark things that you don't ever want
    checked in.  That way Subversion helps you remember :-)

    """

    error_fmt = 'Marker string ("%s") found in %%(filename)s\n' % (
        MARKER_STRING,
        )

    def check_text(self, text):
        return text.find(MARKER_STRING) == -1


class MultipleCheck(Check):
    """Apply the listed checks one after the other.

    checks should be a sequence of Check objects.

    """

    def __init__(self, *checks):
        self.checks = checks

    def __call__(self, change):
        ok = True
        for check in self.checks:
            if not check(change):
                ok = False

        return ok


class PatternCheck(Check):
    """Apply the specified check to all files whose names match regexp.

    regexp -- a regexp pattern which is passed to re.match().

    check -- a Check object.

    """

    def __init__(self, regexp, check):
        self.regexp = re.compile(regexp)
        self.check = check

    def __call__(self, change):
        if self.regexp.match(change.file.filename):
            return self.check(change)
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


