# Copyright (c) 2012 Frank Hellwig
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
Python 3.2 Creole wiki markup parser.

This module parses Cerole wiki version 1.0 markup text into HTML5 or XHTML.
It only outputs HTML tags, not an entire document.  The parser output is
is intended for inclusion in the <body> or <div> section of a page.

This module requires Python 3 and has only been tested with version 3.2.

It provides the CreoleParser class that parses markup from a string or any
object capable of producing lines of text from an iterator (files, etc.).

It also provides the parse() function that instantiates the parser for
applications where a simple function call is all that is required.

By default, the output is HTML5 text.  This means that tags such as <br>,
<img>, and <hr> are not output as self-closing tags.  The resulting HTML5
can be included in a document that having the text/html content type, but
not as an XHTML (or any XML) document.  If XHTML is required, the parser
can be instantiated with the html5 parameter set to False.

Reference: http://www.wikicreole.org/wiki/Creole1.0

Example 1 (instantiating the CreoleParser class):
    
    from creole_parser import CreoleParser

    parser = CreoleParser()

    file = open('markup.creole')
    result = parser.parse(file)
    file.close()

    print(result.heading)   # can be None if no heading was found
    print(result)           # the result is just a normal string

Example 2 (calling the module-level parse() function):

    import creole_parser

    file = open('markup.creole')
    result = creole_parser.parse(file)
    file.close()

    print(result.heading)   # can be None if no heading was found
    print(result)           # the result is just a normal string

Differences between this implementation and the Creole 1.0 specification:

    1. Supports the following additional markup:

            ^^superscript^^
            ,,subscript,,
            __underline__
            ; definition list term
            : definition list description

    2. Consecutive table columns (||, |=|=, or any combination) are
       merged into a single <th> or <td> tag with the colspan attribute.
       The value of the last column indicator determines the type of tag
       so '||=' and '|=|=' both generate a '<th colspan="2">' tag.

    3. Headings can have an id attribute.  This is useful for fragment
       links (e.g., #target) in a table of contents.  The id attribute
       is taken from the text following the last closing equal sign.
       For example, '== System Overview == overview' generates the
       following HTML: '<h2 id="overview">System Overview</h2>'.

    4. Free-standing link URI schemes include 'http', 'https', and 'ftp'.
       The specification does not mention 'https'.  Also, it does not
       specify when a free-standing link ends.  The parser stops when
       it encounters a space, tab, or end-of-line.  It then applies the
       punctuation rules stated in the specification.

    5. The Creole specification labels invalid nesting as unacceptable.
       It does not define what unacceptable means.  The parser does not
       raise an exception on invalid input.  It will always output valid
       HTML even if the input contains errors.

Overall design philosophy: do not raise exceptions on invalid input input
(e.g., invalid nesting or unclosed links and images).  Always output what
was supplied.  If the input is invalid, then do not surround it with tags
and output the invalid text.  The author then sees what was, and was not,
parsed as valid markup because the text still appears, only not as HTML.

The parser processes the wiki markup text in a single-pass without using
regular expression substitution.  It does not require any other modules.
"""

__author__ = 'Frank Hellwig <frank@hellwig.org>'
__all__ = ['CreoleParser', 'ParseResult', 'parse']

# The following are the HTML tags used in the output text.
_HTML_BOLD = 'strong'
_HTML_ITALICS = 'em'
_HTML_SUPERSCRIPT = 'sup'
_HTML_SUBSCRIPT = 'sub'
_HTML_UNDERLINE = 'u'
_HTML_CODE = 'code'
_HTML_BREAK = 'br'
_HTML_LINK = 'a'
_HTML_IMAGE = 'img'
_HTML_PARAGRAPH = 'p'
_HTML_ORDERED_LIST = 'ol'
_HTML_UNORDERED_LIST = 'ul'
_HTML_LIST_ITEM = 'li'
_HTML_DEFINITION_LIST = 'dl'
_HTML_DEFINITION_LIST_TERM = 'dt'
_HTML_DEFINITION_LIST_DESCRIPTION = 'dd'
_HTML_TABLE = 'table'
_HTML_TABLE_ROW = 'tr'
_HTML_TABLE_HEADER = 'th'
_HTML_TABLE_DATA = 'td'
_HTML_PREFORMATTED = 'pre'
_HTML_HORIZONTAL_RULE = 'hr'
_HTML_HEADINGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']

# Content tags do not get a newline character after open or before close.
# They do, however, get one before open and after close.
_CONTENT_TAGS = [
    _HTML_PARAGRAPH,
    _HTML_LIST_ITEM,
    _HTML_DEFINITION_LIST_TERM,
    _HTML_DEFINITION_LIST_DESCRIPTION,
    _HTML_TABLE_HEADER,
    _HTML_TABLE_DATA
]

_CONTENT_TAGS.extend(_HTML_HEADINGS)

# Inline tags do not get any newline characters before or after open and close.
_INLINE_TAGS = [
    _HTML_BOLD,
    _HTML_ITALICS,
    _HTML_SUPERSCRIPT,
    _HTML_SUBSCRIPT,
    _HTML_UNDERLINE,
    _HTML_CODE,
    _HTML_BREAK,
    _HTML_LINK,
    _HTML_IMAGE
]

# Maps markup characters to inline markup tags.
_INLINE_MARKUP_MAP = {
    '**':_HTML_BOLD,
    '//':_HTML_ITALICS,
    '^^':_HTML_SUPERSCRIPT,
    ',,':_HTML_SUBSCRIPT,
    '__':_HTML_UNDERLINE
}

# Self-closing tags are output as <br/> instead of <br> if html5 is False.
_SELF_CLOSING_TAGS = [
    _HTML_BREAK,
    _HTML_IMAGE,
    _HTML_HORIZONTAL_RULE
]

# Each list element is a prefix for a free-standing link.
_FREE_LINKS = ['http://', 'https://', 'ftp://']

# RFC 3986 characters for detecting absolute URIs.
_SCHEME_FIRST = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
_SCHEME_CHARS = _SCHEME_FIRST + '0123456789+-.'


def _escape(s):
    """
    Escape HTML characters and return an escaped string.
    """
    s = s.replace('&', '&amp;')
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    return s


def _is_absolute(uri):
    """
    Determine if the URI is absolute.

    This function uses a narrower definition of absolute than RFC 3986.
    The URI must begine with <scheme>:// rather than just <scheme>: so
    that interwiki links are not considered absolute but are passed to
    the link resolve function (if provided).
    """
    n = len(uri)
    if n < 4:
        return False
    if uri[0] not in _SCHEME_FIRST:
        return False
    i = 1
    while i < n:
        if uri[i] not in _SCHEME_CHARS:
            break
        i += 1
    return uri[i:i + 3] == '://'


def _is_free_link(s):
    """
    Determine if the specified string is a free-standing link.
    """
    for prefix in _FREE_LINKS:
        if s.startswith(prefix):
            return True
    return False


class _LineReader:
    """
    Iterator for reading lines of text.
    """

    def __init__(self, text):
        """
        Set the text for this reader.
        """
        self._text = text
        self._length = len(text)
        self._index = 0

    def __iter__(self):
        """
        Return self.
        """
        return self

    def __next__(self):
        """
        Return the next line of text or raise StopIteration if at end.

        Lines are delimited by CR, LF, or CRLF line terminators. Trailing
        whitespace and the line terminators are not included in the return
        value. Leading whitespace is retained because it is significant in
        preformatted blocks.
        """
        if self._index >= self._length:
            raise StopIteration
        text = self._text
        length = self._length
        index = self._index
        begin = index
        end = index
        while index < length:
            c = text[index]
            if c == '\r':
                index += 1
                if index < length:
                    if text[index] == '\n':
                        index += 1
                break
            elif c == '\n':
                index += 1
                break
            elif c == ' ' or c == '\t':
                index += 1
            else:
                index += 1
                end = index
        self._index = index
        return text[begin:end]


class ParseResult(str):
    """
    The result of parsing Creole wiki markup.

    This class extends the string class and adds the heading attribute.
    """
    def __new__(cls, value, heading):
        return str.__new__(cls, value)
    
    def __init__(self, html, heading):
        self.heading = heading


class CreoleParser:
    """
    Parse Creole wiki markup text into HTML5 text.

    The markup is parsed by calling the parse() method.
    """

    def __init__(self, resolver=None, html5=True):
        """
        Initialize this parser with an optional link resolver and HTML5 flag.

        The resolver parameter, if provided, must be a function taking a URI
        string as input and returning a resolved URI.  All non-absolute link
        and image URIs are passed to the resolver.  A URI beginning with the
        "<scheme>://" sequence is considered absolute.  The slash characters
        are required so that interwiki links are not considered absolute and
        can be interpreted by the resolver.

        If the html5 parameter is set to False, then self-closing tags such
        as <br>, <img>, and <hr> are output as <br/>, <img/>, and <hr/>.
        """
        self._resolver = resolver
        self._html5 = html5

    def parse(self, source):
        """
        Parse Creole wiki markup from the specified source.

        The source argument must be either a string or an object supporting
        the iteration protocol where each iteration produces a line of text.
        Text file objects and sys.stdin are valid sources.

        Returns a ParseResult instance.  This is a string with an additional
        heading attribute.  The heading attribute has the value of the first
        heading in the text.
        """
        self._reset()
        if isinstance(source, str):
            source = _LineReader(source)
        for line in source:
            self._parse_line(line.rstrip())
        self._close_tag()
        return ParseResult(''.join(self._html), self._heading)

    def _reset(self):
        self._stack = []    # tag stack
        self._html = []     # output buffer
        self._heading = None
        self._tag = None

    def _save_state(self):
        result = (self._stack, self._html)
        self._stack = []
        self._html = []
        return result

    def _restore_state(self, state):
        self._stack = state[0]
        self._html = state[1]

    def _merge_state(self, state):
        state[0].extend(self._stack)
        state[1].extend(self._html)
        self._restore_state(state)

    def _parse_line(self, line):
        if _HTML_PREFORMATTED in self._stack:
            if line == '}}}':
                self._close_tag(_HTML_PREFORMATTED)
            else:
                if line.strip() == '}}}':
                    line = line[1:]
                self._html.append(_escape(line))
                self._html.append('\n')
            return
        line = line.strip()
        if line == '':
            self._close_tag()
        elif line == '{{{':
            self._close_tag()
            self._open_tag(_HTML_PREFORMATTED)
        elif line == '----':
            self._close_tag()
            self._add_tag(_HTML_HORIZONTAL_RULE)
        elif line.startswith('='):
            self._close_tag()
            self._parse_heading(line)
        elif line.startswith('#') or line.startswith('*'):
            self._parse_list_item(line)
        elif line.startswith(';') or line.startswith(':'):
            self._parse_definition_list_item(line)
        elif line.startswith('|'):
            self._parse_table_row(line)
        else:
            self._parse_content(line)

    def _parse_content(self, line):
        if (_HTML_PARAGRAPH in self._stack or
                _HTML_ORDERED_LIST in self._stack or
                _HTML_UNORDERED_LIST in self._stack or
                _HTML_DEFINITION_LIST in self._stack):
            if self._tag != _HTML_BREAK:
                self._html.append(' ')
            self._tag = None
        else:
            self._close_tag()
            self._open_tag(_HTML_PARAGRAPH)
        self._parse_fragment(line)

    def _parse_heading(self, line):
        index = 0
        level = 0
        heading = []
        length = len(line)
        while index < length and line[index] == '=':
            level += 1
            index += 1
        if level > 6:
            level = 6
        begin = index
        while index < length:
            if line[index:index + 2] == '~=':
                heading.append(line[begin:index])
                heading.append('=')
                index += 2
                begin = index
            elif line[index] == '=':
                break
            else:
                index += 1
        heading.append(line[begin:index])
        heading = _escape(''.join(heading).strip())
        if not self._heading:
            self._heading = heading
        id = None
        while index < length and line[index] == '=':
            index += 1
        id = line[index:].lstrip()
        if not id:
            id = None
        tag = _HTML_HEADINGS[level - 1]
        self._open_tag(tag, id=id)
        self._html.append(_escape(heading))
        self._close_tag(tag)

    def _parse_list_item(self, line):
        char = line[0]
        index = 0
        length = len(line)
        level = 0
        while index < length and line[index] == char:
            index += 1
            level += 1
        current_level = self._list_level()
        delta = level - current_level
        if delta > 1:  # not allowed to skip increasing levels
            self._parse_content(line)   # treat the error as content
            return                      # this also deconflicts initial bold
        if current_level == 0:
            self._close_tag()
        if delta < 0:
            self._close_tag([_HTML_ORDERED_LIST, _HTML_UNORDERED_LIST], -delta)
            self._close_tag(_HTML_LIST_ITEM)
        elif delta > 0:
            tag = _HTML_ORDERED_LIST if char == '#' else _HTML_UNORDERED_LIST
            self._open_tag(tag)
        else:
            self._close_tag(_HTML_LIST_ITEM)
        self._open_tag(_HTML_LIST_ITEM)
        self._parse_fragment(line[index:])
        
    def _parse_definition_list_item(self, line):
        if _HTML_DEFINITION_LIST not in self._stack:
            self._close_tag()
            self._open_tag(_HTML_DEFINITION_LIST)
        if self._stack[-1] != _HTML_DEFINITION_LIST:
            self._close_tag([_HTML_DEFINITION_LIST_TERM,
                _HTML_DEFINITION_LIST_DESCRIPTION])
        if line[0] == ';':
            self._open_tag(_HTML_DEFINITION_LIST_TERM)
        else:
            self._open_tag(_HTML_DEFINITION_LIST_DESCRIPTION)
        self._parse_fragment(line[1:])

    def _parse_table_row(self, line):
        length = len(line)
        index = 0
        if _HTML_TABLE not in self._stack:
            self._close_tag()
            self._open_tag(_HTML_TABLE)
        self._open_tag(_HTML_TABLE_ROW)
        while index < length:
            colspan = 0
            while index < length and line[index] == '|':
                if line[index:index + 2] == '|=':
                    tag = _HTML_TABLE_HEADER
                    index += 2
                else:
                    tag = _HTML_TABLE_DATA
                    index += 1
                colspan += 1
            if index < length:
                if colspan < 2:
                    colspan = None
                self._open_tag(tag, colspan=colspan)
                index = self._parse_fragment(line, index, delim='|')
                self._close_tag(tag)
        self._close_tag(_HTML_TABLE_ROW)

    def _parse_nowiki(self, line, index):
        length = len(line)
        begin = index
        while index < length:
            if (line[index:index + 3] == '}}}' and
                    (index == length - 3 or line[index + 3] != '}')):
                self._add_text(line, begin, index)
                self._close_tag(_HTML_CODE)
                index += 3
                begin = index
                break
            index += 1
        self._add_text(line, begin, index)
        return index

    def _parse_free_link(self, line, index):
        length = len(line)
        begin = index
        while index < length and line[index] not in ' \t':
            index += 1
        if line[index - 1] in ',.?!:;"\'':
            index -= 1
        href = line[begin:index]
        self._open_tag(_HTML_LINK, href=href)
        self._html.append(_escape(href))
        self._close_tag(_HTML_LINK)
        return index

    def _parse_link(self, line, index):
        length = len(line)
        begin = index
        href = None
        state = self._save_state()
        while index < length and line[index:index + 2] != ']]':
            if line[index] == '|':
                href = self._resolve(line[begin:index].strip())
                self._open_tag(_HTML_LINK, href=href)
                index = self._parse_fragment(line, index + 1, delim=']]')
                self._close_tag(_HTML_LINK)
                break
            index += 1
        if not self._html:  # no pipe was found
            href = self._resolve(line[begin:index])
            self._open_tag(_HTML_LINK, href=href)
            self._html.append(_escape(href))
            self._close_tag(_HTML_LINK)
        # Check that the link was closed properly.
        if index < length:
            self._merge_state(state)
            return index + 2
        else:
            self._restore_state(state)
            self._add_text(line, begin - 2, index)
            return index

    def _parse_image(self, line, index):
        length = len(line)
        begin = saved_index = index
        src = None
        alt = None
        while index < length and line[index:index + 2] != '}}':
            if line[index] == '|' and src is None:
                src = line[begin:index]
                begin = index + 1
            index += 1
        # Check that the image was closed properly.
        if index < length:
            if src is None:
                src = line[begin:index]
            else:
                alt = line[begin:index].strip()
            src = self._resolve(src.strip())
            self._add_tag(_HTML_IMAGE, src=src, alt=alt)
            return index + 2
        else:
            self._add_text(line, saved_index - 2, index)
            return index

    def _parse_fragment(self, line, index=0, delim=''):
        """
        Parse a fragment of the line starting at the specified index.

        The delimiter is an optional string at which parsing stops.
        If the delimiter is encountered, the return value is the index
        of the first character in the delimiter.
        """
        length = len(line)
        delim_length = len(delim)
        escape = False
        begin = index
        while index < length:
            if _HTML_CODE in self._stack:
                index = self._parse_nowiki(line, index)
                begin = index
                continue
            if escape:
                escape = False
                index += 1
                continue
            if line[index] == '~':
                if index + 1 < length and line[index + 1] not in ' \t':
                    self._add_text(line, begin, index)
                    escape = True
                    begin = index + 1
                index += 1
                continue
            if delim_length and line[index:index + delim_length] == delim:
                self._add_text(line, begin, index)
                begin = index
                break
            if line[index:index + 3] == '{{{':
                self._add_text(line, begin, index)
                self._open_tag(_HTML_CODE)
                index += 3
                begin = index
                continue
            if _is_free_link(line[index:]):
                self._add_text(line, begin, index)
                index = self._parse_free_link(line, index)
                begin = index
                continue
            top = self._stack[-1] if self._stack else None
            next_two = line[index:index + 2]
            tag = _INLINE_MARKUP_MAP.get(next_two)
            if tag is not None:
                if top == tag:
                    self._add_text(line, begin, index)
                    self._close_tag(tag)
                    begin = index + 2
                elif tag not in self._stack:
                    self._add_text(line, begin, index)
                    self._open_tag(tag)
                    begin = index + 2
                index += 2
            elif next_two == r'\\':
                self._add_text(line, begin, index)
                self._add_tag(_HTML_BREAK)
                index += 2
                begin = index
            elif next_two == '[[':
                self._add_text(line, begin, index)
                index = self._parse_link(line, index + 2)
                begin = index
            elif next_two == '{{':
                self._add_text(line, begin, index)
                index = self._parse_image(line, index + 2)
                begin = index
            else:
                index += 1
        self._add_text(line, begin, index)
        return index

    def _open_tag(self, tag, **attrs):
        self._add_tag(tag, **attrs)
        self._stack.append(tag)

    def _close_tag(self, until=None, count=1):
        if not isinstance(until, list):
            until = [until]
        while self._stack and count > 0:
            tag = self._stack.pop()
            if tag in _CONTENT_TAGS:
                self._html[-1] = self._html[-1].rstrip()
            if tag not in _CONTENT_TAGS and tag not in _INLINE_TAGS:
                self._add_newline()
            self._html.append('</{0}>'.format(tag))
            if tag not in _INLINE_TAGS:
                self._add_newline()
            if tag in until:
                count -= 1

    def _add_tag(self, tag, **attrs):
        if attrs:
            a = []
            for n, v in attrs.items():
                if v is not None:
                    a.append(' ')
                    a.append(n)
                    a.append('="')
                    a.append(str(v).replace('"', '&quot;'))
                    a.append('"')
            attrs = ''.join(a)
        else:
            attrs = ''
        if tag not in _INLINE_TAGS:
            self._add_newline()
        if not self._html5 and tag in _SELF_CLOSING_TAGS:
            self._html.append('<{0}{1}/>'.format(tag, attrs))
        else:
            self._html.append('<{0}{1}>'.format(tag, attrs))
        if tag not in _CONTENT_TAGS and tag not in _INLINE_TAGS:
            self._add_newline()
        self._tag = tag

    def _add_text(self, text, begin, end):
        if begin < end and begin < len(text):
            text = text[begin:end]
            if self._tag in _CONTENT_TAGS:
                text = text.lstrip()
            self._tag = None
            self._html.append(_escape(text))

    def _add_newline(self):
        if self._html and self._html[-1] != '\n':
            self._html.append('\n')

    def _resolve(self, uri):
        if self._resolver is None:
            return uri
        if _is_absolute(uri):
            return uri
        return self._resolver(uri)

    def _list_level(self):
        level = 0
        for tag in self._stack:
            if tag == _HTML_ORDERED_LIST or tag == _HTML_UNORDERED_LIST:
                level += 1
        return level


def parse(source, resolver=None, html5=True):
    """
    Parse Creole wiki markup from the specified source.  This is a
    module-level function that can be used instead of creating a
    CreoleParser instance.

    The source argument must be either a string or an object supporting
    the iteration protocol where each iteration produces a line of text.
    Text file objects and sys.stdin are valid sources.

    The resolver parameter, if provided, must be a function taking a URI
    string as input and returning a resolved URI.  All non-absolute link
    and image URIs are passed to the resolver.  A URI beginning with the
    "<scheme>://" sequence is considered absolute.  The slash characters
    are required so that interwiki links are not considered absolute and
    can be interpreted by the resolver.

    If the html5 parameter is set to False, then self-closing tags such
    as <br>, <img>, and <hr> are output as <br/>, <img/>, and <hr/>.

    Returns a ParseResult instance.  This is a string with an additional
    heading attribute.  The heading attribute has the value of the first
    heading in the text.
    """
    parser = CreoleParser(resolver, html5)
    return parser.parse(source)


if __name__ == '__main__':
    file = open('test/creole1.0test.txt')
    result = parse(file)
    file.close()
    output_path = 'test/output.html'
    file = open(output_path, 'wt')
    print('Heading:', result.heading)
    print('HTML is in', output_path)
    print(result, file=file)
    file.close()
