"""Check conformance to whitespace rules."""

import sys
import re
import subprocess

import svnlib


# The string that is used as a marker for "don't check me in!".  This
# has to be written strangely to allow this file itself to be checked
# in.
MARKER_STRING = '@''@''@'


class Reporter(object):
    def warning(self, msg):
        sys.stderr.write(msg + '\n')


reporter = Reporter()


class Commit(object):
    def get_logmsg(self):
        """Return the log message for this commit.

        Return the log message for this commit as a single string.  If
        a log message is not available for this type of Commit, raise
        NotImplementedError."""

        raise NotImplementedError()


class GitCommit(Commit):
    def __init__(self, sha1):
        self.sha1 = sha1

    def get_logmsg(self):
        cmd = ['git', 'cat-file', 'commit', self.sha1]
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        (out, err) = p.communicate()
        retcode = p.wait()
        if retcode or err:
            sys.exit('Command failed: %s' % (' '.join(cmd),))
        # The log message follows the first blank line:
        return out[out.index('\n\n') + 2:]


class Check(object):
    def __invert__(self):
        """The inverse of the original check.

        This method is meant mostly for conditions.  Please note that
        for checks, this might need to be overloaded to avoid error
        output.

        """

        return CheckNot(self)

    def __and__(self, other):
        return CheckAnd(self, other)

    def __or__(self, other):
        return CheckOr(self, other)


class CheckNot(Check):
    """A check that is the logical inverse of another check.

    This is mostly intended to be used for conditions.

    """

    def __init__(self, check):
        self.check = check

    def __call__(self, *args, **kw):
        return not self.check(*args, **kw)


class CheckAnd(Check):
    """A check that is the logical 'and' of other checks.

    Checks are short-circuited.

    """

    def __init__(self, *checks):
        self.checks = checks

    def __call__(self, *args, **kw):
        for check in self.checks:
            if not check(*args, **kw):
                return False

        return True


class CheckOr(Check):
    """A check that is the logical 'or' of other checks.

    Checks are short-circuited.

    """

    def __init__(self, *checks):
        self.checks = checks

    def __call__(self, *args, **kw):
        for check in self.checks:
            if check(*args, **kw):
                return True

        return False


class MultipleCheck(Check):
    """Apply the listed checks one after the other.

    checks should be a sequence of Check objects.  The result is True
    iff all checks returned True (but without short-circuiting).

    """

    def __init__(self, *checks):
        self.checks = checks

    def __call__(self, *args, **kw):
        ok = True
        for check in self.checks:
            if not check(*args, **kw):
                ok = False

        return ok


class LogMessageCheck(Check):
    """A check that a log message is OK."""

    def __call__(self, logmsg, silent=False):
        """Return True iff commit passes test."""

        raise NotImplementedError()


class LogMarkerStringCheck(LogMessageCheck):
    """Don't allow a log message that includes the marker string."""

    def __call__(self, logmsg, silent=False):
        ok = MARKER_STRING not in logmsg
        if not ok and not silent:
            reporter.warning('Log message contains marker string ("%s")' % (MARKER_STRING,))
        return ok


class CommitCheck(Check):
    """A check that can be applied to a full commit."""

    def __call__(self, repository, commit, silent=False):
        """Return True iff commit passes test."""

        raise NotImplementedError()


class CommitChangeCheck(CommitCheck):
    """A CommitCheck that applies a ChangeCheck to each Change."""

    def __init__(self, check):
        self.check = check

    def __call__(self, repository, commit, silent=False):
        ok = True

        for change in repository.get_changes(commit):
            if not self.check(change, silent):
                ok = False

        return ok


class ChangeCheck(Check):
    """A check that can be applied to a Change.

    Checks can be combined with '~', '&', and '|'.

    """

    def __call__(self, change, silent=False):
        """Return True iff change passes test."""

        raise NotImplementedError()


class SilentCheck(ChangeCheck):
    def __init__(self, check):
        self.check = check

    def __call__(self, change, silent=False):
        return self.check(change, silent=True)


class TextChangeCheck(ChangeCheck):
    """A ChangeCheck that applies a TextCheck to any NewTextChanges."""

    def __init__(self, check):
        self.check = check

    def __call__(self, change, silent=False):
        if isinstance(change, svnlib.NewTextChange):
            return self.check(change, change.get_new_text(), silent)
        else:
            return True


class TextCheck(Check):
    """A Check that is purely based on the text of the file."""

    def __call__(self, change, text, silent=False):
        ok = self.check_text(text)

        if not ok and not silent:
            reporter.warning(self.error_fmt % {'filename' : change.file})

        return ok

    def check_text(self, text):
        """Return True iff text is OK."""

        raise NotImplementedError()


class TrailingWhitespaceCheck(TextCheck):
    """Don't allow whitespace at the end of a line or the end of the file."""

    trailing_ws_re = re.compile(r'[ \t]+$', re.MULTILINE)

    error_fmt = 'Trailing whitespace in %(filename)s'

    def __init__(self):
        pass

    def check_text(self, text):
        return not self.trailing_ws_re.search(text)


class LeadingWhitespaceCheck(TextCheck):
    """Don't allow whitespace at the start of a line."""

    trailing_ws_re = re.compile(r'^[ \t]', re.MULTILINE)

    error_fmt = 'Leading whitespace in %(filename)s'

    def check_text(self, text):
        return not self.trailing_ws_re.search(text)


class BlankLineCheck(TextCheck):
    """Don't allow lines that are completely empty."""

    blank_line_re = re.compile(r'^\n', re.MULTILINE)

    error_fmt = 'Blank line in %(filename)s'

    def check_text(self, text):
        return not self.blank_line_re.search(text)


class TabCheck(TextCheck):
    """Don't allow any tab characters."""

    error_fmt = 'Tab(s) in %(filename)s'

    def check_text(self, text):
        return text.find('\t') == -1


class CRCheck(TextCheck):
    """Don't allow any carriage returns characters."""

    error_fmt = 'Carriage return(s) in %(filename)s'

    def check_text(self, text):
        return text.find('\r') == -1


class UnterminatedLineCheck(TextCheck):
    """Don't allow the last line to be unterminated."""

    error_fmt = 'Last line of %(filename)s is unterminated'

    def check_text(self, text):
        return (not text) or text[-1] == '\n'


class MarkerStringCheck(TextCheck):
    """Don't allow files to be checked in if they include the marker string.

    This string can be used to mark things that you don't ever want
    checked in.  That way Subversion helps you remember :-)

    """

    error_fmt = 'Marker string ("%s") found in %%(filename)s' % (
        MARKER_STRING,
        )

    def check_text(self, text):
        return text.find(MARKER_STRING) == -1


class FilenameCheck(ChangeCheck):
    """A ChangeCheck that is based on a regexp match of the change's filename."""

    def __init__(self, regexp):
        self.regexp = re.compile(regexp)

    def __call__(self, change, silent=False):
        ok = bool(self.regexp.match(change.file.filename))

        if not ok and not silent:
            reporter.warning(
                'File %s does not match %r'
                % (change.file, self.regexp.pattern,)
                )

        return ok


class PropertyCheck(ChangeCheck):
    """A ChangeCheck that is based on a regexp-match of a Subversion property.

    regexp is a regular expression pattern (as a string) which must
    match the whole property value."""

    def __init__(self, property, regexp):
        self.property = property
        self.regexp = re.compile('^' + regexp + '$')

    def __call__(self, change, silent=False):
        value = change.repository.get_property(
            change.commit, change.file.filename, self.property
            )
        if value is None:
            # Treat absent values the same as '':
            value = ''
        ok = bool(self.regexp.match(value))

        if not ok and not silent:
            reporter.warning(
                'File %s, property %s does not match %r'
                % (change.file, self.property, self.regexp.pattern,)
                )

        return ok


class MimeTypeCheck(ChangeCheck):
    """A ChangeCheck that compares the file's mime type with a constant."""

    def __init__(self, mime_type):
        self.mime_type = mime_type

    def __call__(self, change, silent=False):
        mime_type = change.repository.get_mime_type(
            change.commit, change.file.filename
            )
        ok = (mime_type == self.mime_type)

        if not ok and not silent:
            reporter.warning(
                'Mime type of file %s should be %r'
                % (change.file, self.mime_type,)
                )

        return ok


def if_then(condition, check):
    """If condition is met, apply check.

    condition -- a ChangeCheck object that will be evaluated silently.

    check -- a ChangeCheck object that will be evaluated only if
        condition returns True.

    This is the logical equivalent of 'condition -> check' or '~
    condition | check', except that condition is evaluated silently.

    """

    return SilentCheck(~condition) | check


allchecks = MultipleCheck(
    LogMarkerStringCheck(),
    CommitChangeCheck(
        if_then(
            ~PropertyCheck('ignore-checks', r'.+'),
            MultipleCheck(
                if_then(
                    # Java source files:
                    FilenameCheck(r'.*\.java$')

                    # Python/Jython source files:
                    | FilenameCheck(r'.*\.py$')
                    | MimeTypeCheck('text/x-python')

                    # C/C++ source files:
                    | FilenameCheck(r'.*\.(c|cc|cpp|h)$')

                    # shell scripts:
                    | FilenameCheck(r'.*\.sh$')
                    | MimeTypeCheck('application/x-sh')

                    # Java properties files:
                    | FilenameCheck(r'.*\.properties$')

                    # RPM spec files:
                    | FilenameCheck(r'.*\.spec$')
                    ,
                    TextChangeCheck(
                        MultipleCheck(
                            TrailingWhitespaceCheck(),
                            TabCheck(),
                            CRCheck(),
                            UnterminatedLineCheck(),
                            MarkerStringCheck(),
                            )
                        )
                    ),

                # Makefile-like files:
                if_then(
                    FilenameCheck(r'Makefile(\.module)?$')
                    | MimeTypeCheck('text/x-makefile'),
                    TextChangeCheck(
                        MultipleCheck(
                            TrailingWhitespaceCheck(),
                            CRCheck(),
                            UnterminatedLineCheck(),
                            MarkerStringCheck(),
                            )
                        )
                    ),

                # Text files:
                if_then(
                    FilenameCheck(r'.*\.txt$'),
                    TextChangeCheck(
                        MultipleCheck(
                            TrailingWhitespaceCheck(),
                            CRCheck(),
                            UnterminatedLineCheck(),
                            MarkerStringCheck(),
                            )
                        )
                    ),
                )
            )
        ),
    )


